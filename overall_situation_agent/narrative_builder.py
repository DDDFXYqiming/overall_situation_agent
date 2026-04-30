from __future__ import annotations

import json
import logging
import math
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
]


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


def _join_items(items: list[dict], limit: int = 3) -> str:
    visible = _top(items, limit)
    return "、".join(f"{item['key']}（{_n(item['count'])}）" for item in visible) if visible else "无"


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
    member_cluster = _top(result.get("biz_member_cluster", []), 3)
    tertiary = _top(result.get("tertiary", []), 3)
    lines: list[str] = []
    if service_type and service_total:
        top = service_type[0]
        lines.append(
            f"业务维度上，服务类型「{top.get('key', '未标注')}」占比 {_ratio(top.get('count', 0), service_total)}，高频服务类型集中在 {_join_items(service_type, 3)}。"
        )
    if member_cluster or tertiary:
        lines.append(
            f"结合涉及业务/会员类型，热点集中在 {_join_items(member_cluster, 3)}，对应三级痛点主要是 {_join_items(tertiary, 3)}。"
        )
    return lines


def _trend_matchday_business_lines(result: dict[str, Any], daily: list[dict]) -> list[str]:
    if not daily:
        return []
    schedule = result.get("schedule") or {}
    matchdays = [day for day in daily if _matchday(day)]
    non_matchdays = [day for day in daily if not _matchday(day)]
    peak = max(daily, key=lambda item: item.get("count", 0), default=None)
    lines: list[str] = []
    if schedule.get("status") == "loaded":
        source_name = schedule.get("source_name") or "赛程文件"
        if matchdays and non_matchdays:
            matchday_avg = sum(day.get("count", 0) for day in matchdays) / len(matchdays)
            non_matchday_avg = sum(day.get("count", 0) for day in non_matchdays) / len(non_matchdays)
            lines.append(f"已加载赛程文件《{source_name}》；赛事日日均问题量 {matchday_avg:.1f} 件，非赛事日日均 {non_matchday_avg:.1f} 件。")
        elif matchdays:
            lines.append(f"已加载赛程文件《{source_name}》；当前趋势命中 {len(matchdays)} 个赛事日，赛事日合计问题量 {_n(sum(day.get('count', 0) for day in matchdays))} 件。")
        else:
            lines.append(f"已加载赛程文件《{source_name}》，但当前趋势窗口未命中赛事日。")
    else:
        lines.append(_schedule_message(result))
    if peak:
        match_text = _matchday_summary(peak) if _matchday(peak) else "非赛事日"
        lines.append(
            f"峰值日 {peak.get('date')} 问题量 {_n(peak.get('count', 0))} 件，赛事日标注为{match_text}；"
            f"当日一级/二级/三级热点分别为 {_join_items(peak.get('top_primary', []), 2)}、{_join_items(peak.get('top_secondary', []), 2)}、{_join_items(peak.get('top_tertiary', []), 3)}。"
        )
        lines.append(
            f"峰值日业务热点集中在服务类型 {_join_items(peak.get('top_service_type', []), 2)}，涉及业务/会员类型为 {_join_items(peak.get('top_member_cluster', []), 2)}。"
        )
    return lines


def _schedule_message(result: dict[str, Any]) -> str:
    schedule = result.get("schedule") or {}
    return str(schedule.get("message") or "未提供赛程文件，1.2 未标注赛事日。")


def _summary_payload(result: dict[str, Any]) -> dict[str, Any]:
    daily = result.get("daily", [])
    peak_day = max(daily, key=lambda item: item.get("count", 0), default=None)
    neg_peak = max(daily, key=lambda item: item.get("negative_ratio", 0), default=None)
    anomalies = _sorted_anomaly_days(result.get("anomalies", []))[:5]
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
    cause_examples = []
    for item in result.get("top_tertiary_examples", [])[:3]:
        cause_examples.append(
            {
                "issue": item.get("key"),
                "count": item.get("count"),
                "appeals": _top(item.get("top_appeals", []), 3),
                "quotes": [sample.get("content_excerpt", "") for sample in item.get("samples", [])[:2]],
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
        "primary": _top(result.get("primary", []), 5),
        "secondary": _top(result.get("secondary", []), 5),
        "tertiary": _top(result.get("tertiary", []), 5),
        "emotion": _top(result.get("emotion", []), 5),
        "service_type": _top(result.get("service_type", []), 5),
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
        "operation_need_examples": result.get("operation_need_examples", [])[:5],
        "member_cluster_examples": result.get("member_cluster_examples", [])[:5],
        "latent_need_examples": result.get("latent_need_examples", [])[:5],
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
    refund = next((item.get("count", 0) for item in unlabeled_analysis.get("has_refund_demand", []) if item.get("key") == "是"), 0)
    escalation = next((item.get("count", 0) for item in unlabeled_analysis.get("has_escalation", []) if item.get("key") == "是"), 0)
    lines = [
        f"本次共纳入 {_n(total_with_unlabeled)} 条工单，其中 {_n(unlabeled_total)} 条（{unlabeled_pct}）一/二/三级标签未标注，已从问题分布统计中排除。",
    ]
    if emotion or appeal or csp_name:
        lines.append(
            f"从未标注工单的内容结构看，情绪以 {_join_keys(emotion, 2)} 为主，诉求集中在 {_join_keys(appeal, 2)}，主要渠道/终端线索为 {_join_keys(csp_name, 2)}，更适合作为待回补标签池单独治理。"
        )
    if refund or escalation:
        lines.append(f"风险上存在退费诉求 {_n(refund)} 件、升级投诉倾向 {_n(escalation)} 件，建议优先回补标签后再并入主问题池复盘。")
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
    cause_examples = result.get("top_tertiary_examples", [])[:3]

    narratives = {key: [] for key in NARRATIVE_KEYS}
    narratives["unlabeled_distribution_summary"] = _unlabeled_distribution_summary(result)
    narratives["unlabeled_trend_summary"] = _unlabeled_trend_summary(result)
    if total:
        summary = [
            f"本周期共纳入 {_n(total)} 条反馈/投诉工单，核心问题集中在 {_join_items(tertiary, 3)}，需要优先围绕订购、退订、权益和赛事体验链路定位。",
            f"一级问题主要集中在 {_join_items(primary, 2)}，二级问题主要集中在 {_join_items(secondary, 2)}，用于快速判断资源优先级。",
        ]
        if peak_day:
            summary.append(f"趋势峰值出现在 {peak_day['date']}，当日 {_n(peak_day.get('count', 0))} 件，峰值日主要问题为 {_join_items(peak_day.get('top_tertiary', []), 3)}。")
        narratives["executive_summary"] = summary
        distribution_lines = [
            f"本周期共纳入 {_n(total)} 条反馈/投诉工单，一级、二级、三级问题分布基于已完成标签标注的工单统计。",
            f"一级问题最集中的是 {_join_items(primary, 2)}；二级层面主要集中在 {_join_items(secondary, 2)}。",
            f"三级问题中 {_join_items(tertiary, 3)} 是当前最值得优先定位的高频痛点。",
        ]
        distribution_lines.extend(_business_dimension_lines(result))
        narratives["distribution_conclusion"] = distribution_lines
        if emotion:
            narratives["distribution_conclusion"].append(f"情绪标签以 {_join_items(emotion, 3)} 为主，说明当前投诉以负向体验反馈为主。")

    if primary:
        total_primary = sum(item.get("count", 0) for item in primary) or 1
        top_item = primary[0]
        narratives["primary_overview"] = [
            f"一级问题中「{top_item['key']}」提及 {_n(top_item['count'])} 次，在当前一级标签中占比 {_pct(top_item['count'], total_primary)}。",
            f"一级问题整体呈现“头部集中、其余分散”的结构，前几类问题主要是 {_join_items(primary, 3)}。",
        ]
    if secondary:
        total_secondary = sum(item.get("count", 0) for item in secondary) or 1
        top_item = secondary[0]
        narratives["secondary_overview"] = [
            f"二级问题中「{top_item['key']}」提及 {_n(top_item['count'])} 次，占当前二级标签的 {_pct(top_item['count'], total_secondary)}。",
            f"从二级问题集中度看，当前主要压力点落在 {_join_items(secondary, 3)} 这些具体业务环节。",
        ]
    if tertiary:
        total_tertiary = sum(item.get("count", 0) for item in tertiary) or 1
        top_item = tertiary[0]
        narratives["tertiary_overview"] = [
            f"三级问题中「{top_item['key']}」提及 {_n(top_item['count'])} 次，占当前三级标签的 {_pct(top_item['count'], total_tertiary)}。",
            f"三级问题更能直接反映用户痛点，当前高频问题主要集中在 {_join_items(tertiary, 3)}。",
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
        for item in cause_examples[:2]:
            appeals = _join_items(item.get("top_appeals", []), 2)
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
            f"当前共识别到 {_n(len(anomalies))} 个明显异动日，按日环比降序、问题量降序、日期升序展示全部异动日。",
            f"该异动日的问题量为 {_n(first['count'])} 件，日环比 {first.get('day_over_day_growth', 0) * 100:.1f}%。",
        ]
    else:
        narratives["anomaly_summary"] = ["当前周期未识别到满足阈值的明显异动日，整体波动相对平稳。"]
    return narratives


def _sanitize_lines(parsed: dict[str, Any], fallback: dict[str, list[str]]) -> dict[str, list[str]]:
    cleaned: dict[str, list[str]] = {}
    unlabeled_markers = ("未标注一二三级标签", "一/二/三级标签未标注", "未标注工单", "未标注数据")
    out_of_scope_markers = ("隐性需求", "运营举措", "会员类型聚类", "年龄段", "性别分布", "客群")
    for key in NARRATIVE_KEYS:
        value = parsed.get(key)
        if isinstance(value, list):
            lines = [str(item).strip() for item in value if str(item).strip()]
            if key in {"distribution_conclusion", "trend_conclusion"}:
                lines = [line for line in lines if not any(marker in line for marker in unlabeled_markers)]
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
            cleaned[key] = lines[:4] if lines else fallback[key]
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
                "每个字段值都必须是字符串数组，每条 1 句，带具体数字或日期。"
                "风格要求：减少表格化罗列，改成简洁的数据分析句。"
                "字段必须完整输出：executive_summary、distribution_conclusion、primary_overview、secondary_overview、"
                "tertiary_overview、journey_summary、operation_need_summary、member_cluster_summary、"
                "case_summary、cause_summary、voice_summary、trend_conclusion、anomaly_summary、"
                "unlabeled_distribution_summary、unlabeled_trend_summary。"
                "注意：输入数据中包含未标注一二三级标签工单（一/二/三级标签未标注的工单），这些数据已被排除在分布统计和趋势计算之外。"
                "distribution_conclusion 和 trend_conclusion 只能写已标注数据的主结论，严禁出现未标注相关内容。"
                "未标注内容只能写入 unlabeled_distribution_summary 与 unlabeled_trend_summary。"
                "未标注 summary 第一条保留数量和占比说明，其余只输出 2-3 条基于情绪、客户诉求、渠道/CSP、退费/升级风险、趋势峰值归纳出的文字洞察；不要写 TOP5 列表、典型样例、逐条原声、运营举措、隐性需求或会员/客群分析。"
                "总量口径：payload.total 和 payload.total_with_unlabeled 均表示含未标注工单的总工单量；payload.labeled_total 仅表示已完成一/二/三级标签标注并用于标签分布统计的工单量。"
                "凡是写'总工单量'、'共纳入'、'反馈/投诉总量'，必须使用 payload.total，不要使用 labeled_total。"
                "报告只负责“一、整体情况”的 1.1 问题分布概览和 1.2 投诉趋势与异动表现。"
                "distribution_conclusion 必须包含业务维度分析：基于 service_type 写占比，并结合 biz_member_cluster 和三级问题说明业务痛点。"
                "trend_conclusion 必须结合赛事日、赛程文件或比赛信息、峰值日问题量、一级/二级/三级标签和业务维度。"
                "不要生成'本次查询'、'口径说明'、'分析要点'、'展示方式'或'计算说明'相关文案。"
                "executive_summary 只围绕总工单量、一级/二级/三级问题分布、TOP 三级问题、趋势峰值、异动节点和赛事日，不要把运营举措、隐性需求、会员聚类、年龄、性别或客群分析写成报告重点。"
                "文字表述要求：使用'未标注一二三级标签'或'一/二/三级标签未标注'，避免使用'未标注数据'或'一级标签缺失'。"
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    response = llm.chat(
        messages,
        temperature=0.2,
        timeout_seconds=llm.report_timeout,
        max_retries=llm.report_max_retries,
        max_tokens=llm.report_max_tokens,
    )
    if response.used_fallback:
        logger.warning("Narrative builder fell back because LLM was unavailable")
        return fallback
    parsed = parse_json_object(response.content)
    if not parsed:
        logger.warning("Narrative builder fell back because LLM output was not valid JSON")
        return fallback
    return _sanitize_lines(parsed, fallback)
