from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from .llm_client import OpenAICompatibleClient, parse_json_object

logger = logging.getLogger(__name__)


NARRATIVE_KEYS = [
    "executive_summary",
    "distribution_conclusion",
    "primary_overview",
    "secondary_overview",
    "tertiary_overview",
    "journey_summary",
    "operation_need_summary",
    "member_cluster_summary",
    "case_summary",
    "cause_summary",
    "voice_summary",
    "trend_conclusion",
    "anomaly_summary",
    "unlabeled_distribution_summary",
    "unlabeled_trend_summary",
    "trend_chart_summary",
    "trend_voice_summary",
    "cause_voice_sample_summaries",
    "cause_field_summaries",
    "trend_voice_sample_summaries",
]

LLM_NARRATIVE_KEYS = [
    "distribution_conclusion",
    "cause_summary",
    "voice_summary",
    "trend_conclusion",
    "trend_chart_summary",
    "trend_voice_summary",
    "cause_voice_sample_summaries",
    "cause_field_summaries",
    "trend_voice_sample_summaries",
]

REPORT_LLM_TIMEOUT_FLOOR = 180
REPORT_LLM_MAX_TOKENS_FLOOR = 8000


def _n(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _pct(part: float, whole: float) -> str:
    if not whole:
        return "0.0%"
    return f"{part / whole * 100:.1f}%"


def _top(items: list[dict], limit: int = 5) -> list[dict]:
    return [item for item in items if item.get("count", 0) > 0][:limit]


def _top_with_share(items: list[dict], limit: int = 5) -> list[dict]:
    total = _sum_counts(items)
    buckets = []
    for item in _top(items, limit):
        count = item.get("count", 0)
        bucket = dict(item)
        bucket["share"] = count / total if total else 0
        bucket["display"] = f"{item.get('key', '未标注')}（共{_n(count)}条，占比{_pct(count, total)}）"
        buckets.append(bucket)
    return buckets


def _join_items(items: list[dict], limit: int = 3, total: int | None = None) -> str:
    visible = _top(items, limit)
    denominator = total if total is not None else _sum_counts(items)
    return (
        "、".join(
            f"{item['key']}（共{_n(item['count'])}条，占比{_pct(item.get('count', 0), denominator)}）"
            for item in visible
        )
        if visible
        else "无"
    )


def _join_keys(items: list[dict], limit: int = 3) -> str:
    visible = _top(items, limit)
    return "、".join(str(item.get("key")) for item in visible if item.get("key")) if visible else "无"


def _sum_counts(items: list[dict]) -> int:
    return int(sum(item.get("count", 0) for item in items))


def _ratio(part: float, whole: float) -> str:
    return f"{part / whole * 100:.1f}%" if whole else "0.0%"


def _matchday(day: dict[str, Any]) -> dict[str, Any] | None:
    if day.get("is_matchday") and day.get("matchday"):
        return day["matchday"]
    return None


def _matchday_summary(day: dict[str, Any]) -> str:
    payload = _matchday(day)
    return str(payload.get("match_summary", "")).strip() if payload else ""


def _sorted_anomaly_days(anomalies: list[dict]) -> list[dict]:
    return sorted(
        anomalies,
        key=lambda item: (
            -float(item.get("day_over_day_growth") or 0),
            -int(item.get("count") or 0),
            str(item.get("date") or ""),
        ),
    )


def _business_dimension_lines(result: dict[str, Any]) -> list[str]:
    service_type = _top(result.get("service_type", []), 3)
    service_total = _sum_counts(result.get("service_type", []))
    tertiary = _top(result.get("tertiary", []), 3)
    lines: list[str] = []
    if service_type and service_total:
        top = service_type[0]
        issue_text = "、".join(str(item.get("key")) for item in tertiary if item.get("key")) or "订购、权益和观看体验问题"
        lines.append(
            f"业务维度上，服务类型「{top.get('key', '未标注')}」占比 {_ratio(top.get('count', 0), service_total)}，用户反馈主要落在{issue_text}，说明当前压力不是单点功能异常，而是订购退订、权益兑现和赛事观看体验在同一服务链路上叠加。"
        )
    return lines


def _trend_matchday_business_lines(result: dict[str, Any], daily: list[dict]) -> list[str]:
    if not daily:
        return []
    matchdays = [day for day in daily if _matchday(day)]
    non_matchdays = [day for day in daily if not _matchday(day)]
    lines: list[str] = []

    if matchdays and non_matchdays:
        matchday_avg = sum(day.get("count", 0) for day in matchdays) / len(matchdays)
        non_matchday_avg = sum(day.get("count", 0) for day in non_matchdays) / len(non_matchdays)
        matchday_dates = "、".join(sorted(str(day.get("date", "")) for day in matchdays if day.get("date")))
        lines.append(
            f"有比赛的是 {len(matchdays)} 天（{matchday_dates}），赛事日日均问题量 {matchday_avg:.1f} 件，非赛事日日均 {non_matchday_avg:.1f} 件。"
        )
    elif matchdays:
        matchday_dates = "、".join(sorted(str(day.get("date", "")) for day in matchdays if day.get("date")))
        total = sum(day.get("count", 0) for day in matchdays)
        lines.append(
            f"有比赛的是 {len(matchdays)} 天（{matchday_dates}），赛事日合计问题量 {_n(total)} 件。"
        )
    elif (result.get("schedule") or {}).get("status") != "loaded":
        lines.append(_schedule_message(result))
    peak_day = max(daily, key=lambda item: item.get("count", 0), default=None)
    if peak_day:
        services = _join_keys(peak_day.get("top_service_type", []), 2)
        issues = _join_keys(peak_day.get("top_tertiary", []), 3)
        if services != "无" or issues != "无":
            lines.append(
                f"从业务表现看，峰值附近的反馈集中在{services}类服务场景，用户表达的问题多围绕{issues}，赛事前后的即时观看预期会放大退订、权益和多端使用链路的不满。"
            )
    return lines


def _schedule_message(result: dict[str, Any]) -> str:
    schedule = result.get("schedule") or {}
    return str(schedule.get("message") or "未提供赛程文件，1.2 未标注赛事日。")


def _trend_voice_examples(daily: list[dict], anomalies: list[dict], limit: int = 3) -> list[dict]:
    if not daily:
        return []
    peak = max(daily, key=lambda item: item.get("count", 0), default=None)
    peak_date = str(peak.get("date")) if peak else ""
    anomaly_dates = {str(item.get("date")) for item in anomalies if item.get("date")}
    matchday_samples = [day for day in daily if _matchday(day) and day.get("samples")]
    matchday_samples.sort(
        key=lambda item: (
            item.get("date") == peak_date,
            str(item.get("date")) in anomaly_dates,
            item.get("count", 0),
            item.get("negative_ratio", 0),
        ),
        reverse=True,
    )
    selected = []
    seen_dates: set[str] = set()
    for day in matchday_samples:
        date = str(day.get("date") or "")
        if not date or date in seen_dates:
            continue
        seen_dates.add(date)
        selected.append(
            {
                "date": date,
                "count": day.get("count", 0),
                "match_summary": _matchday_summary(day),
                "top_tertiary": _top(day.get("top_tertiary", []), 3),
                "quotes": [sample.get("content_excerpt", "") for sample in day.get("samples", [])[:2]],
                "samples": day.get("samples", [])[:2],
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _summary_payload(result: dict[str, Any]) -> dict[str, Any]:
    daily = result.get("daily", [])
    peak_day = max(daily, key=lambda item: item.get("count", 0), default=None)
    neg_peak = max(daily, key=lambda item: item.get("negative_ratio", 0), default=None)
    anomalies = _sorted_anomaly_days(result.get("anomalies", []))[:5]
    trend_voice_examples = _trend_voice_examples(daily, result.get("anomalies", []))
    matchdays = []
    for day in daily:
        matchday = day.get("matchday")
        if day.get("is_matchday") and matchday:
            matchdays.append(
                {
                    "date": day["date"],
                    "summary": matchday.get("match_summary"),
                    "count": day.get("count", 0),
                }
            )
        if len(matchdays) >= 5:
            break
    cause_source = (result.get("top_tertiary_cause_evidence") or {}).get("items") or result.get("top_tertiary_examples", [])
    cause_examples = []
    for item in cause_source[:5]:
        cause_examples.append(
            {
                "issue": item.get("key"),
                "count": item.get("count"),
                "share": item.get("share"),
                "appeals": _top(item.get("top_appeals") or item.get("top_customer_appeals", []), 5),
                "customer_keywords": _top(item.get("top_customer_keywords", []), 8),
                "cs_actions": _top(item.get("top_cs_actions", []), 5),
                "cs_keywords": _top(item.get("top_cs_keywords", []), 8),
                "samples": [
                    {
                        "service_time": sample.get("service_time"),
                        "scene_service_type": sample.get("scene_service_type"),
                        "scene_emotion": sample.get("scene_emotion"),
                        "content": sample.get("content") or sample.get("content_excerpt"),
                        "cs_reply": sample.get("cs_reply") or sample.get("cs_reply_excerpt"),
                        "customer_key_appeal": sample.get("customer_key_appeal") or sample.get("appeal"),
                        "customer_keywords": sample.get("customer_keywords"),
                        "cs_key_action": sample.get("cs_key_action") or sample.get("operation_action"),
                        "cs_keywords": sample.get("cs_keywords"),
                    }
                    for sample in item.get("samples", [])
                ],
            }
        )

    labeled_total = result.get("total", 0)
    unlabeled_analysis = result.get("unlabeled_analysis", {})
    unlabeled_total = unlabeled_analysis.get("unlabeled_total", 0)
    total_with_unlabeled = result.get("total_with_unlabeled", labeled_total)
    unlabeled_ratio = unlabeled_total / total_with_unlabeled if total_with_unlabeled else 0
    unlabeled_trend_analysis = result.get("unlabeled_trend_analysis", {})

    return {
        "total": total_with_unlabeled,
        "labeled_total": labeled_total,
        "total_with_unlabeled": total_with_unlabeled,
        "unlabeled_total": unlabeled_total,
        "unlabeled_ratio": unlabeled_ratio,
        "unlabeled_samples": unlabeled_analysis.get("samples", [])[:5],
        "unlabeled_emotion": unlabeled_analysis.get("emotion", [])[:3],
        "unlabeled_province": unlabeled_analysis.get("province", [])[:5],
        "unlabeled_csp_name": unlabeled_analysis.get("csp_name", [])[:5],
        "unlabeled_operation_action": unlabeled_analysis.get("operation_action", [])[:5],
        "unlabeled_latent_need": unlabeled_analysis.get("latent_need", [])[:5],
        "unlabeled_customer_key_appeal": unlabeled_analysis.get("customer_key_appeal", [])[:5],
        "unlabeled_has_refund_demand": unlabeled_analysis.get("has_refund_demand", []),
        "unlabeled_has_escalation": unlabeled_analysis.get("has_escalation", []),
        "unlabeled_trend_daily": unlabeled_trend_analysis.get("daily", []),
        "unlabeled_trend_peak_day": unlabeled_trend_analysis.get("peak_day"),
        "unlabeled_trend_emotion_peak": unlabeled_trend_analysis.get("emotion_peak_day"),
        "primary": _top_with_share(result.get("primary", []), 5),
        "secondary": _top_with_share(result.get("secondary", []), 5),
        "tertiary": _top_with_share(result.get("tertiary", []), 5),
        "emotion": _top_with_share(result.get("emotion", []), 5),
        "service_type": _top_with_share(result.get("service_type", []), 5),
        "refund": _top(result.get("refund", []), 5),
        "escalation": _top(result.get("escalation", []), 5),
        "label_group": _top(result.get("label_group", []), 5),
        "insight_dimension": _top(result.get("insight_dimension", []), 5),
        "customer_key_appeal": _top(result.get("customer_key_appeal", []), 5),
        "cs_key_action": _top(result.get("cs_key_action", []), 5),
        "operation_action": _top(result.get("operation_action", []), 5),
        "biz_member_cluster": _top(result.get("biz_member_cluster", []), 5),
        "marketing_activity_page": _top(result.get("marketing_activity_page", []), 5),
        "marketing_activity_match_status": _top(result.get("marketing_activity_match_status", []), 5),
        "marketing_activity_match_keywords": _top(result.get("marketing_activity_match_keywords", []), 5),
        "age_ranges": _top(result.get("age_ranges", []), 6),
        "gender": _top(result.get("gender", []), 5),
        "latent_need": _top(result.get("latent_need_examples", []), 5),
        "time_period": _top(result.get("time_period", []), 5),
        "match_label": _top(result.get("match_label", []), 5),
        "avg_duration_minutes": result.get("avg_duration_minutes"),
        "peak_day": peak_day,
        "negative_peak_day": neg_peak,
        "anomalies": anomalies,
        "matchdays": matchdays,
        "schedule_message": _schedule_message(result),
        "cause_examples": cause_examples,
        "cause_evidence_sample_strategy": (result.get("top_tertiary_cause_evidence") or {}).get("sample_strategy", {}),
        "trend_voice_examples": [
            {
                "date": item.get("date"),
                "match_summary": item.get("match_summary"),
                "top_tertiary": item.get("top_tertiary", []),
                "quotes": item.get("quotes", []),
            }
            for item in trend_voice_examples
        ],
        "operation_need_examples": result.get("operation_need_examples", [])[:5],
        "member_cluster_examples": result.get("member_cluster_examples", [])[:5],
        "latent_need_examples": result.get("latent_need_examples", [])[:5],
        "sample_texts_raw": (result.get("sample_texts") or {}).get("raw", [])[:40],
        "sample_texts_by_primary": (result.get("sample_texts") or {}).get("by_primary", [])[:24],
        "sample_texts_by_service_type": (result.get("sample_texts") or {}).get("by_service_type", [])[:20],
        "sample_texts_matchday": (result.get("sample_texts") or {}).get("matchday", [])[:10],
    }


def _unlabeled_distribution_summary(result: dict[str, Any]) -> list[str]:
    unlabeled_analysis = result.get("unlabeled_analysis", {})
    unlabeled_total = unlabeled_analysis.get("unlabeled_total", 0)
    if not unlabeled_total:
        return []
    total_with_unlabeled = result.get("total_with_unlabeled", result.get("total", 0))
    unlabeled_pct = _pct(unlabeled_total, total_with_unlabeled)
    emotion = unlabeled_analysis.get("emotion", [])
    csp_name = unlabeled_analysis.get("csp_name", [])
    appeal = unlabeled_analysis.get("customer_key_appeal", [])
    lines = [
        f"本次共纳入 {_n(total_with_unlabeled)} 条工单，其中 {_n(unlabeled_total)} 条（{unlabeled_pct}）一/二/三级标签未标注，已从问题分布统计中排除。",
    ]
    if emotion or appeal or csp_name:
        lines.append(
            f"从未标注工单的内容结构看，情绪以 {_join_keys(emotion, 2)} 为主，诉求集中在 {_join_keys(appeal, 2)}，主要渠道/终端线索为 {_join_keys(csp_name, 2)}，更适合作为待回补标签池单独治理。"
        )
    return lines[:4]


def _unlabeled_trend_summary(result: dict[str, Any]) -> list[str]:
    unlabeled_trend = result.get("unlabeled_trend_analysis", {})
    unlabeled_total = unlabeled_trend.get("unlabeled_total", 0)
    if not unlabeled_total:
        return []
    total_with_unlabeled = result.get("total_with_unlabeled", result.get("total", 0))
    unlabeled_pct = _pct(unlabeled_total, total_with_unlabeled)
    daily = unlabeled_trend.get("daily", [])
    peak = unlabeled_trend.get("peak_day")
    emotion_peak = unlabeled_trend.get("emotion_peak_day")
    lines = [
        f"本周期共 {_n(unlabeled_total)} 条一/二/三级标签未标注工单，占原始总量的 {unlabeled_pct}，未纳入上述趋势计算。",
    ]
    if daily:
        lines.append(
            f"时间上覆盖 {daily[0]['date']} 至 {daily[-1]['date']}；峰值出现在 {peak['date']}（{_n(peak.get('count', 0))} 件）时，建议核查当日是否存在批量活动咨询、权益问题或导入漏标。"
            if peak
            else f"时间上覆盖 {daily[0]['date']} 至 {daily[-1]['date']}，建议作为独立漏标趋势跟踪。"
        )
    if emotion_peak:
        lines.append(f"情绪高峰出现在 {emotion_peak['date']}，负向情绪占比 {emotion_peak.get('negative_ratio', 0) * 100:.1f}%，可优先抽样校验该日未标注文本的真实问题类型。")
    if daily and len(daily) > 1:
        midpoint = len(daily) // 2
        first_half = daily[:midpoint]
        second_half = daily[midpoint:]
        first_avg = sum(day.get("count", 0) for day in first_half) / len(first_half) if first_half else 0
        second_avg = sum(day.get("count", 0) for day in second_half) / len(second_half) if second_half else 0
        if second_avg > first_avg * 1.5:
            lines.append("趋势上后半周期明显抬升，提示后续导入或标注流程可能出现阶段性漏标。")
        elif first_avg > second_avg * 1.5:
            lines.append("趋势上前半周期更集中，后半周期有所回落，建议核对早期批次的标签抽取规则。")
    return lines[:4]


def _fallback_narratives(result: dict[str, Any]) -> dict[str, list[str]]:
    labeled_total = result.get("total", 0)
    total = result.get("total_with_unlabeled", labeled_total)
    primary = _top(result.get("primary", []), 3)
    secondary = _top(result.get("secondary", []), 3)
    tertiary = _top(result.get("tertiary", []), 3)
    emotion = _top(result.get("emotion", []), 3)
    label_group = _top(result.get("label_group", []), 3)
    insight_dimension = _top(result.get("insight_dimension", []), 3)
    appeal = _top(result.get("customer_key_appeal", []), 3)
    cs_action = _top(result.get("cs_key_action", []), 3)
    operation_action = _top(result.get("operation_action", []), 3)
    member_cluster = _top(result.get("biz_member_cluster", []), 3)
    marketing_page = _top(result.get("marketing_activity_page", []), 3)
    marketing_status = _top(result.get("marketing_activity_match_status", []), 3)
    age_ranges = _top(result.get("age_ranges", []), 3)
    gender = _top(result.get("gender", []), 3)
    latent_need = _top(result.get("latent_need_examples", []), 3)
    refund_yes = next((item.get("count", 0) for item in result.get("refund", []) if item.get("key") == "是"), 0)
    escalation_yes = next((item.get("count", 0) for item in result.get("escalation", []) if item.get("key") == "是"), 0)
    avg_duration = result.get("avg_duration_minutes")
    daily = result.get("daily", [])
    peak_day = max(daily, key=lambda item: item.get("count", 0), default=None)
    neg_peak = max(daily, key=lambda item: item.get("negative_ratio", 0), default=None)
    anomalies = result.get("anomalies", [])
    cause_examples = result.get("top_tertiary_examples", [])[:5]
    matchdays = [day for day in daily if _matchday(day)]
    primary_total = _sum_counts(result.get("primary", []))
    secondary_total = _sum_counts(result.get("secondary", []))
    tertiary_total = _sum_counts(result.get("tertiary", []))
    emotion_total = _sum_counts(result.get("emotion", []))

    narratives = {key: [] for key in NARRATIVE_KEYS}
    narratives["unlabeled_distribution_summary"] = _unlabeled_distribution_summary(result)
    narratives["unlabeled_trend_summary"] = _unlabeled_trend_summary(result)
    if total:
        summary = [
            f"本周期共纳入 {_n(total)} 条反馈/投诉工单，核心问题集中在 {_join_items(tertiary, 3, tertiary_total)}，需要优先围绕订购、退订、权益和赛事体验链路定位。",
            f"一级问题主要集中在 {_join_items(primary, 2, primary_total)}，二级问题主要集中在 {_join_items(secondary, 2, secondary_total)}，用于快速判断资源优先级。",
        ]
        if peak_day:
            summary.append(f"趋势峰值出现在 {peak_day['date']}，当日 {_n(peak_day.get('count', 0))} 件，峰值日主要问题为 {_join_items(peak_day.get('top_tertiary', []), 3)}。")
        narratives["executive_summary"] = summary
        distribution_lines = [
            f"本周期共纳入 {_n(total)} 条反馈/投诉工单，一级、二级、三级问题分布基于已完成标签标注的工单统计。",
            f"一级问题最集中的是 {_join_items(primary, 2, primary_total)}；二级层面主要集中在 {_join_items(secondary, 2, secondary_total)}。",
            f"三级问题中 {_join_items(tertiary, 3, tertiary_total)} 是当前最值得优先定位的高频痛点。",
        ]
        distribution_lines.extend(_business_dimension_lines(result))
        narratives["distribution_conclusion"] = distribution_lines
        if emotion:
            narratives["distribution_conclusion"].append(f"情绪标签以 {_join_items(emotion, 3, emotion_total)} 为主，说明当前投诉以负向体验反馈为主。")

    if primary:
        top_item = primary[0]
        narratives["primary_overview"] = [
            f"一级问题中 {top_item['key']}（共{_n(top_item['count'])}条，占比{_pct(top_item['count'], primary_total)}）最集中。",
            f"一级问题整体呈现“头部集中、其余分散”的结构，前几类问题主要是 {_join_items(primary, 3, primary_total)}。",
        ]
    if secondary:
        top_item = secondary[0]
        narratives["secondary_overview"] = [
            f"二级问题中 {top_item['key']}（共{_n(top_item['count'])}条，占比{_pct(top_item['count'], secondary_total)}）最集中。",
            f"从二级问题集中度看，当前主要压力点落在 {_join_items(secondary, 3, secondary_total)} 这些具体业务环节。",
        ]
    if tertiary:
        top_item = tertiary[0]
        narratives["tertiary_overview"] = [
            f"三级问题中 {top_item['key']}（共{_n(top_item['count'])}条，占比{_pct(top_item['count'], tertiary_total)}）最集中。",
            f"三级问题更能直接反映用户痛点，当前高频问题主要集中在 {_join_items(tertiary, 3, tertiary_total)}。",
        ]
    if tertiary or insight_dimension:
        avg_text = (
            f"，平均处理耗时约 {float(avg_duration):.1f} 分钟"
            if isinstance(avg_duration, (int, float)) and not math.isnan(float(avg_duration))
            else ""
        )
        narratives["journey_summary"] = [
            f"问题链路上，高频三级问题为 {_join_items(tertiary, 3)}，标签组集中在 {_join_items(label_group, 3)}，对应洞察维度集中在 {_join_items(insight_dimension, 3)}{avg_text}。",
            f"主诉求集中在 {_join_items(appeal, 2)}，客服动作集中在 {_join_items(cs_action, 2)}；应联动退费诉求、升级倾向和典型原声判断触发原因。",
        ]
    else:
        narratives["journey_summary"] = ["当前未提取到足够的问题链路字段，无法形成稳定的归因摘要。"]
    if operation_action or latent_need:
        narratives["operation_need_summary"] = [
            f"运营举措中高频项为 {_join_items(operation_action, 3)}，相关隐性需求主要是 {_join_items(latent_need, 3)}。",
            f"营销活动页面和匹配状态线索分别集中在 {_join_items(marketing_page, 2)}、{_join_items(marketing_status, 2)}；若运营举措对应投诉量高，应进一步拆分活动告知、权益兑现、扣费退订、赛事体验四类原因。",
        ]
    else:
        narratives["operation_need_summary"] = ["当前数据未提供有效运营举措或隐性需求字段，报告仅保留展示口径。"]
    if member_cluster:
        narratives["member_cluster_summary"] = [
            f"会员/业务聚类投诉最集中在 {_join_items(member_cluster, 3)}，可按会员类型拆分订购、退订、权益、赛事观看体验。",
            f"年龄段和性别分布可辅助识别客群差异，当前高频年龄段为 {_join_items(age_ranges, 2)}，性别分布为 {_join_items(gender, 2)}。",
        ]
    else:
        narratives["member_cluster_summary"] = ["当前未提取到有效会员/业务聚类字段，无法按会员类型形成排序结论。"]
    if cause_examples:
        lines = []
        for item in cause_examples[:5]:
            appeals = _join_keys(item.get("top_appeals", []), 2)
            lines.append(f"围绕「{item['key']}」的诉求主要是 {appeals}，说明用户更关注退费、订购和权益处理等直接结果。")
        narratives["cause_summary"] = lines or ["当前未提取到足够的三级问题原因线索。"]
        first = cause_examples[0]
        narratives["voice_summary"] = [
            f"从用户原声看，「{first['key']}」相关反馈最密集，文本中重复出现退费、误订购、自动续费等明确诉求。",
            "建议结合原声样例判断问题属于资费争议、流程体验问题还是权益兑现问题，再决定优先治理顺序。",
        ]
        narratives["case_summary"] = [
            f"典型案例优先关注「{first['key']}」相关样例，因其数量最高且常伴随明确诉求。",
            "案例阅读时建议同时看工单内容、客户关键诉求和三级标签路径，以判断问题属于资费争议、流程体验还是权益兑现。",
        ]
    else:
        narratives["case_summary"] = ["当前未提取到可展示的典型案例样本。"]
    narratives["cause_voice_sample_summaries"] = _build_cause_voice_sample_summaries(cause_examples)
    narratives["cause_field_summaries"] = _build_cause_field_summaries(cause_examples)
    if peak_day and neg_peak:
        trend_lines = [
            f"{peak_day['date']} 的问题量达到峰值 {_n(peak_day['count'])} 件，是当前趋势上的最高波峰。",
            f"{neg_peak['date']} 的负向情绪占比最高，为 {neg_peak.get('negative_ratio', 0) * 100:.1f}%，说明该日用户情绪最激烈。",
        ]
        trend_lines.extend(_trend_matchday_business_lines(result, daily))
        narratives["trend_conclusion"] = trend_lines
    if anomalies:
        first = _sorted_anomaly_days(anomalies)[0]
        narratives["anomaly_summary"] = [
            "异动节点按日环比增幅、问题量和日期综合排序，报告仅展示最需要优先复盘的前三个节点。",
            f"排序最高的异动日为 {first['date']}，日环比 {first.get('day_over_day_growth', 0) * 100:.1f}%。",
        ]
    else:
        narratives["anomaly_summary"] = ["当前周期未识别到满足阈值的明显异动日，整体波动相对平稳。"]
    narratives["trend_chart_summary"] = _build_trend_chart_summary_fallback(daily, matchdays, anomalies)
    narratives["trend_voice_summary"] = _build_trend_voice_summary_fallback(matchdays)
    narratives["trend_voice_sample_summaries"] = _build_trend_voice_sample_summaries(_trend_voice_examples(daily, anomalies))
    return narratives


def _extract_plain_messages(value: Any) -> list[str]:
    text = str(value or "")
    if not text:
        return []
    messages = []
    for match in re.findall(r'["“]消息内容["”]\s*[:：]\s*["“](.*?)["”]', text):
        cleaned = re.sub(r"\s+", " ", match).strip(" ;；,，。")
        if cleaned and not any(marker in cleaned for marker in ("正在为您转接人工", "当前人工MM有点忙", "请稍后", "请耐心等待")):
            messages.append(cleaned)
    if not messages and '"消息内容"' not in text:
        cleaned = re.sub(r"\s+", " ", text).strip(" ;；,，。")
        if cleaned:
            messages.append(cleaned)
    deduped = []
    seen = set()
    for message in messages:
        if message in seen:
            continue
        seen.add(message)
        deduped.append(message)
    return deduped


def _sample_summary(value: Any, issue: str = "") -> str:
    messages = _extract_plain_messages(value)
    if not messages:
        return "样例主要反映用户在相关业务办理或观看过程中遇到体验阻断。"
    combined = " ".join(messages[:3])
    points: list[str] = []
    if any(word in combined for word in ("退费", "退款", "退订", "不退")):
        points.append("退订或退费处理结果不符合预期")
    if any(word in combined for word in ("电视", "TV", "tv", "投屏", "大屏")):
        points.append("电视端或投屏观看权益受阻")
    if any(word in combined for word in ("手机", "多端", "四屏", "互通")):
        points.append("手机端与电视端权益互通规则不清")
    if any(word in combined for word in ("价格", "168", "219", "218", "258", "套餐", "补差")):
        points.append("套餐价格和权益差异理解成本高")
    if any(word in combined for word in ("会员", "权益", "兑换", "钻石")):
        points.append("会员权益兑现与用户预期存在落差")
    if any(word in combined for word in ("扣费", "订购", "误购", "自动续费", "不知情")):
        points.append("订购扣费或自动续费流程引发争议")
    if not points:
        points.append("相关业务办理或观看过程存在体验阻断")
    topic = f"「{issue}」" if issue else "该问题"
    return f"样例中，用户围绕{topic}主要反馈{'，并且'.join(dict.fromkeys(points[:3]))}。"


def _build_cause_voice_sample_summaries(cause_examples: list[dict]) -> list[str]:
    summaries = []
    for item in cause_examples:
        sample = (item.get("samples") or [{}])[0]
        summaries.append(_sample_summary(sample.get("content_excerpt", ""), str(item.get("key") or "")))
    return summaries


def _keys_text(items: list[dict], limit: int = 4) -> str:
    keys = [str(item.get("key") or "").strip() for item in (items or [])[:limit] if str(item.get("key") or "").strip()]
    return "、".join(keys) if keys else "未形成稳定高频项"


def _sample_group_summary(samples: list[dict], issue: str) -> str:
    joined = " ".join(
        str(sample.get("content") or sample.get("content_excerpt") or "").strip()
        for sample in samples[:5]
        if str(sample.get("content") or sample.get("content_excerpt") or "").strip()
    )
    if not joined:
        return f"工单内容与客服回复：{issue}下的样本主要体现业务办理或观看过程中的体验阻断，客服侧以记录、解释或转派处理为主。"
    base = _sample_summary(joined, issue)
    reply_terms = "、".join(
        dict.fromkeys(
            str(sample.get("cs_reply") or sample.get("cs_reply_excerpt") or "").strip()
            for sample in samples[:3]
            if str(sample.get("cs_reply") or sample.get("cs_reply_excerpt") or "").strip()
        )
    )
    if reply_terms:
        return f"工单内容与客服回复：{base}客服回复侧多围绕规则解释、问题核查、投诉记录或退费处理展开。"
    return f"工单内容与客服回复：{base}客服侧处理结果在样本中不够明确，容易让用户继续追问处理进度。"


def _build_cause_field_summaries(cause_examples: list[dict]) -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []
    for item in cause_examples[:5]:
        issue = str(item.get("key") or item.get("issue") or "三级问题").strip()
        samples = item.get("samples") or []
        appeals = _keys_text(item.get("top_appeals") or item.get("appeals") or item.get("top_customer_appeals") or [], 4)
        customer_keywords = _keys_text(item.get("top_customer_keywords") or item.get("customer_keywords") or [], 5)
        cs_actions = _keys_text(item.get("top_cs_actions") or item.get("cs_actions") or [], 4)
        cs_keywords = _keys_text(item.get("top_cs_keywords") or item.get("cs_keywords") or [], 5)
        summaries.append(
            {
                "issue": issue,
                "content_reply_summary": _sample_group_summary(samples, issue),
                "appeal_keyword_summary": (
                    f"客户诉求与关键词：用户诉求主要集中在{appeals}，关键词集中在{customer_keywords}，说明用户更关注问题能否被退费、取消、核实或恢复权益。"
                ),
                "cs_action_keyword_summary": (
                    f"客服处理动作与关键词：客服动作主要表现为{cs_actions}，处理关键词集中在{cs_keywords}，整体更偏向解释规则、提交核查和记录投诉。"
                ),
            }
        )
    return summaries


def _clean_generated_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if any(marker in text for marker in ("消息内容", "发送方", "[{", "{\"", "'消息内容'")):
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _sanitize_cause_field_summaries(value: Any, fallback: Any) -> list[dict[str, str]]:
    fallback_items = [item for item in (fallback or []) if isinstance(item, dict)]
    raw_items = value if isinstance(value, list) else []
    cleaned_items: list[dict[str, str]] = []
    for idx in range(max(len(raw_items), len(fallback_items))):
        raw = raw_items[idx] if idx < len(raw_items) else {}
        base = fallback_items[idx] if idx < len(fallback_items) else {}
        if not isinstance(raw, dict):
            raw = {}
        issue = _clean_generated_text(raw.get("issue")) or _clean_generated_text(base.get("issue"))
        content_reply = _clean_generated_text(raw.get("content_reply_summary")) or _clean_generated_text(base.get("content_reply_summary"))
        appeal_keyword = _clean_generated_text(raw.get("appeal_keyword_summary")) or _clean_generated_text(base.get("appeal_keyword_summary"))
        cs_action_keyword = _clean_generated_text(raw.get("cs_action_keyword_summary")) or _clean_generated_text(base.get("cs_action_keyword_summary"))
        if not any([issue, content_reply, appeal_keyword, cs_action_keyword]):
            continue
        cleaned_items.append(
            {
                "issue": issue,
                "content_reply_summary": content_reply,
                "appeal_keyword_summary": appeal_keyword,
                "cs_action_keyword_summary": cs_action_keyword,
            }
        )
    return cleaned_items[:5]


def _build_trend_voice_sample_summaries(matchdays: list[dict]) -> list[str]:
    summaries = []
    for day in matchdays[:3]:
        samples = day.get("samples") or []
        sample_text = "；".join(
            _sample_summary(sample.get("content_excerpt", ""), _join_keys(day.get("top_tertiary", []), 1))
            for sample in samples[:2]
            if sample.get("content_excerpt")
        )
        summaries.append(sample_text or "该赛事日样例主要反映用户在比赛前后集中咨询和反馈观看、订购或权益处理问题。")
    return summaries


def _build_trend_chart_summary_fallback(daily: list[dict], matchdays: list[dict], anomalies: list[dict]) -> list[str]:
    if not daily:
        return ["当前趋势窗口内无可绘制的每日趋势数据。"]
    peak = max(daily, key=lambda item: item.get("count", 0))
    neg_peak = max(daily, key=lambda item: item.get("negative_ratio", 0))
    lines = [
        f"折线图显示问题量峰值出现在 {peak['date']}，当日提及 {_n(peak['count'])} 件。",
        f"负向情绪占比最高日为 {neg_peak['date']}，占比 {_pct(neg_peak.get('negative_ratio', 0), 1.0)}。",
    ]
    if matchdays and len(matchdays) > 1:
        matchday_total = sum(d.get("count", 0) for d in matchdays)
        lines.append(f"赛事日合计提及 {matchday_total} 件，比赛前后的咨询、退订和权益反馈更容易形成集中波动。")
    if anomalies:
        strongest = max(anomalies, key=lambda item: item.get("day_over_day_growth", 0))
        lines.append(f"异动中增幅最高节点为 {strongest['date']}，日环比 {_pct(strongest.get('day_over_day_growth', 0), 1.0)}。")
    return lines


def _build_trend_voice_summary_fallback(matchdays: list[dict]) -> list[str]:
    if not matchdays:
        return ["当前趋势窗口内未提取到带赛事日标注的样例原声。"]
    lead = matchdays[0]
    lead_issues = "、".join(item.get("key", "") for item in lead.get("top_tertiary", [])[:3] if item.get("key")) or "无"
    return [
        f"赛事日样例中，{lead['date']} 的投诉最集中，共 {_n(lead['count'])} 件；相关原声主要围绕 {lead_issues} 展开。",
        "从赛事日原声看，用户更容易在比赛前后集中反馈退订、权益兑换、订购失败和覆盖范围等即时体验问题。",
    ]


def _sanitize_lines(parsed: dict[str, Any], fallback: dict[str, list[str]]) -> dict[str, list[str]]:
    cleaned: dict[str, list[str]] = {}
    unlabeled_markers = ("未标注一二三级标签", "一/二/三级标签未标注", "未标注工单", "未标注数据")
    out_of_scope_markers = ("隐性需求", "运营举措", "会员类型聚类", "年龄段", "性别分布", "客群")

    def is_service_type_listing(line: str) -> bool:
        return (
            (("投诉类型占" in line or "投诉类工单占" in line) and ("咨询类型" in line or "咨询类" in line))
            or "高频服务类型集中" in line
            or bool(re.search(r"服务类型.*（共[\d,]+条", line))
        )

    def is_label_count_listing(line: str) -> bool:
        return (
            "已标注工单" in line
            or bool(re.search(r"(一级|二级|三级)问题.*[\d,]+条.*占", line))
            or bool(re.search(r"（?共?[\d,]+条，?占", line)) and any(marker in line for marker in ("一级", "二级", "三级", "计费争议", "权益使用"))
        )

    def clean_business_line(line: str) -> str:
        cleaned = re.sub(r"超过\s*[\d,]+名用户", "大量用户", line)
        cleaned = re.sub(r"约提及", "不少用户提及", cleaned)
        cleaned = re.sub(r"[\d,]+名用户", "多名用户", cleaned)
        cleaned = re.sub(r"（?共?[\d,]+条(?:投诉|工单)?）?", "", cleaned)
        cleaned = re.sub(r"引发\s*投诉", "也较突出", cleaned)
        cleaned = re.sub(r"产生\s*投诉", "也较突出", cleaned)
        cleaned = cleaned.replace("问题突出（", "问题突出，")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = cleaned.replace("，其中多端体验差异，", "，其中多端体验差异也较突出，")
        return cleaned

    def merge_distribution_lines(lines: list[str]) -> list[str]:
        fallback_lines = fallback.get("distribution_conclusion", [])
        has_real_label_lines = any("（共" in line and "占比" in line for line in fallback_lines[:3])
        if not has_real_label_lines:
            return lines
        label_lines = fallback_lines[:3]
        natural_business_lines = [
            line
            for line in lines
            if not is_service_type_listing(line)
            and not is_label_count_listing(line)
            and not any(marker in line for marker in unlabeled_markers)
            and any(marker in line for marker in ("业务", "用户", "订购", "退订", "权益", "电视端", "观看", "客服"))
        ]
        natural_business_lines = [clean_business_line(line) for line in natural_business_lines]
        if not natural_business_lines:
            natural_business_lines = [
                line
                for line in fallback_lines
                if "业务维度" in line and not is_service_type_listing(line)
            ]
        emotion_line = next((line for line in fallback_lines if "情绪" in line), "")
        merged = label_lines + natural_business_lines[:2]
        if emotion_line:
            merged.append(emotion_line)
        return merged

    for key in NARRATIVE_KEYS:
        if key == "cause_field_summaries":
            cleaned[key] = _sanitize_cause_field_summaries(parsed.get(key), fallback.get(key, []))
            continue
        value = parsed.get(key)
        if isinstance(value, list):
            lines = [str(item).strip() for item in value if str(item).strip()]
            if key in {"cause_voice_sample_summaries", "trend_voice_sample_summaries"}:
                lines = [
                    line
                    for line in lines
                    if not any(marker in line for marker in ("消息内容", "发送方", "[{", "{\"", "'消息内容'"))
                ]
            if key in {"distribution_conclusion", "trend_conclusion"}:
                lines = [line for line in lines if not any(marker in line for marker in unlabeled_markers)]
            if key == "distribution_conclusion":
                lines = merge_distribution_lines(lines)
            if key == "distribution_conclusion" and not any("业务" in line for line in lines):
                lines.extend([line for line in fallback[key] if "业务" in line][:1])
            if key == "trend_conclusion" and not any("赛事" in line for line in lines):
                lines.extend([line for line in fallback[key] if "赛事" in line][:2])
            if key == "executive_summary":
                lines = [line for line in lines if not any(marker in line for marker in out_of_scope_markers)]
            if key == "distribution_conclusion" and len(lines) > 4 and not any("业务" in line for line in lines[:4]):
                business_line = next((line for line in lines if "业务" in line), None)
                if business_line:
                    lines = lines[:3] + [business_line]
            if key == "trend_conclusion" and len(lines) > 4 and not any("赛事" in line for line in lines[:4]):
                schedule_line = next((line for line in lines if "赛事" in line), None)
                if schedule_line:
                    lines = lines[:3] + [schedule_line]
            if not lines:
                cleaned[key] = fallback[key]
            elif key == "distribution_conclusion":
                cleaned[key] = lines[:6]
            else:
                cleaned[key] = lines[:4]
        else:
            cleaned[key] = fallback[key]
    return cleaned


def build_report_narratives(result: dict[str, Any], llm: OpenAICompatibleClient) -> dict[str, list[str]]:
    fallback = _fallback_narratives(result)
    if not llm.enabled or not getattr(llm, "report_enabled", False):
        return fallback

    payload = _summary_payload(result)
    messages = [
        {
            "role": "system",
            "content": (
                "你是投诉分析报告撰写助手，只能基于输入事实生成中文分析文案，只输出 JSON。"
                "不要编造不存在的数据、日期、球队、趋势或结论。"
                "除 cause_field_summaries 外，每个字段值都必须是字符串数组，每条 1 句，带具体数字或日期。"
                "cause_field_summaries 必须是对象数组，每个对象包含 issue、content_reply_summary、appeal_keyword_summary、cs_action_keyword_summary。"
                "风格要求：减少机械罗列，改成信息量更高的自然语言分析句。"
                "只输出这些字段：distribution_conclusion、cause_summary、voice_summary、trend_conclusion、"
                "trend_chart_summary、trend_voice_summary、cause_voice_sample_summaries、cause_field_summaries、trend_voice_sample_summaries；"
                "其他字段不要输出，系统会用本地稳定统计补齐。"
                "注意：输入数据中包含未标注一二三级标签工单（一/二/三级标签未标注的工单），这些数据已被排除在分布统计和趋势计算之外。"
                "distribution_conclusion 和 trend_conclusion 只能写已标注数据的主结论，严禁出现未标注相关内容。"
                "未标注内容只能写入 unlabeled_distribution_summary 与 unlabeled_trend_summary。"
                "未标注 summary 第一条保留数量和占比说明，其余只输出 2-3 条基于情绪、客户诉求、渠道/CSP、退费/升级风险、趋势峰值归纳出的文字洞察；不要写 TOP5 列表、典型样例、逐条原声、运营举措、隐性需求或会员/客群分析。"
                "总量口径：payload.total 和 payload.total_with_unlabeled 均表示含未标注工单的总工单量；payload.labeled_total 仅表示已完成一/二/三级标签标注并用于标签分布统计的工单量。"
                "凡是写'总工单量'、'共纳入'、'反馈/投诉总量'，必须使用 payload.total，不要使用 labeled_total。"
                "凡是在正文里提及一级、二级、三级标签的数量，必须使用'标签（共X条，占比Y%）'格式；payload.primary、payload.secondary、payload.tertiary 中的 display 字段可直接使用。"
                "报告只负责“一、整体情况”的 1.1 问题分布概览和 1.2 投诉趋势与异动表现。"
                "distribution_conclusion 只写 1-2 条业务维度自然语言洞察，不要写一级/二级/三级标签统计，不要写'已标注工单共...'，不要写服务类型 TOP 列表；必须结合 sample_texts_raw、sample_texts_by_service_type 和三级问题，用自然语言概括用户在订购、退订、权益、观看端或客服处理链路上的真实痛点。"
                "trend_conclusion 必须结合赛事日、赛程文件或比赛信息、峰值日问题量、一级/二级/三级标签和业务维度；业务维度部分同样要基于 sample_texts_matchday 和原文样本自然概括，不要列服务类型 TOP 列表。"
                "不要生成'本次查询'、'口径说明'、'分析要点'、'展示方式'或'计算说明'相关文案。"
                "executive_summary 只围绕总工单量、一级/二级/三级问题分布、TOP 三级问题、趋势峰值、异动节点和赛事日，不要把运营举措、隐性需求、会员聚类、年龄、性别或客群分析写成报告重点。"
                "payload 中的 sample_texts_raw、sample_texts_by_primary、sample_texts_by_service_type 和 sample_texts_matchday 是从原始工单正文抽取的代表性原文样本，可参考用于生成自然语言描述。"
                "payload.cause_examples 是 TOP 三级标签原因分析证据包：统计数字来自 ES，samples 中的 content、cs_reply、customer_key_appeal、customer_keywords、cs_key_action、cs_keywords 是清洗后的代表样本。"
                "写 cause_summary、cause_voice_sample_summaries 和 cause_field_summaries 时必须基于该证据包归纳原因；不要复制原文，不要展示 JSON，不要把客服回复整段贴出，也不要用引号复述用户原句或客服原句。"
                "cause_field_summaries 必须按 payload.cause_examples 顺序逐个输出 TOP5 三级标签，每个对象的三个 summary 分别总结："
                "content_reply_summary 总结 samples.content 和 samples.cs_reply 体现的用户问题与客服回应方式；"
                "appeal_keyword_summary 总结 customer_key_appeal 与 customer_keywords 体现的客户关键诉求和诉求关键词；"
                "cs_action_keyword_summary 总结 cs_key_action 与 cs_keywords 体现的客服关键处理动作和处理关键词。"
                "每个 summary 写 2 句左右，字数不少于 70 个中文字符，不要只列词。"
                "distribution_conclusion 的业务维度不要写成'投诉类型占...咨询类型占...'或服务类型 TOP 列表；要把服务类型数据转译为业务痛点判断。"
                "在 distribution_conclusion、cause_summary、voice_summary、trend_conclusion、trend_voice_summary 中，"
                "请优先基于这些原始文本用自然语言描述业务结论，而非仅罗列统计数据。"
                "cause_summary 只写原因和诉求类型，不要写各诉求的条数或占比。"
                "cause_voice_sample_summaries 必须按 payload.cause_examples 顺序输出自然语言摘要；trend_voice_sample_summaries 必须按 payload.trend_voice_examples 顺序输出自然语言摘要。"
                "这两个 sample_summaries 字段严禁复制原文、JSON、消息列表或'发送方/消息内容'结构，也不要直接引用用户原句，只能写概括后的自然语言。"
                "文字表述要求：使用'未标注一二三级标签'或'一/二/三级标签未标注'，避免使用'未标注数据'或'一级标签缺失'。"
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    last_content = ""
    for attempt in range(2):
        response = llm.chat(
            messages,
            temperature=0.2,
            timeout_seconds=max(llm.report_timeout, REPORT_LLM_TIMEOUT_FLOOR),
            max_retries=max(llm.report_max_retries, 1),
            max_tokens=max(llm.report_max_tokens, REPORT_LLM_MAX_TOKENS_FLOOR),
        )
        if response.used_fallback:
            logger.warning("Narrative builder fell back because LLM was unavailable")
            return fallback
        last_content = response.content
        parsed = parse_json_object(response.content)
        if parsed:
            return _sanitize_lines(parsed, fallback)
        messages = [
            *messages,
            {"role": "assistant", "content": response.content[:4000]},
            {
                "role": "user",
                "content": (
                    "上一次输出不是合法 JSON。请只输出一个 JSON object，不要 Markdown、不要解释、不要代码块；"
                    "必须包含要求的字段，cause_field_summaries 必须是对象数组。"
                ),
            },
        ]

    logger.warning("Narrative builder fell back because LLM output was not valid JSON: %s", last_content[:500])
    return fallback
