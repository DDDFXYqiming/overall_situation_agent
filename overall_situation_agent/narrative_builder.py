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


def _schedule_message(result: dict[str, Any]) -> str:
    schedule = result.get("schedule") or {}
    return str(schedule.get("message") or "未提供赛程文件，1.2 未标注赛事日。")


def _summary_payload(result: dict[str, Any]) -> dict[str, Any]:
    daily = result.get("daily", [])
    peak_day = max(daily, key=lambda item: item.get("count", 0), default=None)
    neg_peak = max(daily, key=lambda item: item.get("negative_ratio", 0), default=None)
    anomalies = result.get("anomalies", [])[:3]
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

    return {
        "total": result.get("total", 0),
        "primary": _top(result.get("primary", []), 5),
        "secondary": _top(result.get("secondary", []), 5),
        "tertiary": _top(result.get("tertiary", []), 5),
        "emotion": _top(result.get("emotion", []), 5),
        "service_type": _top(result.get("service_type", []), 5),
        "refund": _top(result.get("refund", []), 5),
        "escalation": _top(result.get("escalation", []), 5),
        "insight_dimension": _top(result.get("insight_dimension", []), 5),
        "operation_action": _top(result.get("operation_action", []), 5),
        "biz_member_cluster": _top(result.get("biz_member_cluster", []), 5),
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


def _fallback_narratives(result: dict[str, Any]) -> dict[str, list[str]]:
    total = result.get("total", 0)
    primary = _top(result.get("primary", []), 3)
    secondary = _top(result.get("secondary", []), 3)
    tertiary = _top(result.get("tertiary", []), 3)
    emotion = _top(result.get("emotion", []), 3)
    insight_dimension = _top(result.get("insight_dimension", []), 3)
    operation_action = _top(result.get("operation_action", []), 3)
    member_cluster = _top(result.get("biz_member_cluster", []), 3)
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
    if total:
        summary = [
            f"本周期共纳入 {_n(total)} 条反馈/投诉，核心问题集中在 {_join_items(tertiary, 3)}，需要优先围绕订购、退订、权益和赛事体验链路定位。",
            f"风险诉求中退费 {_n(refund_yes)} 件、升级投诉倾向 {_n(escalation_yes)} 件；运营举措高频项为 {_join_items(operation_action, 3)}。",
            f"会员/业务聚类主要集中在 {_join_items(member_cluster, 3)}，隐性需求 TOP 为 {_join_items(latent_need, 3)}。",
        ]
        if peak_day:
            summary.append(f"趋势峰值出现在 {peak_day['date']}，当日 {_n(peak_day.get('count', 0))} 件，峰值日主要问题为 {_join_items(peak_day.get('top_tertiary', []), 3)}。")
        narratives["executive_summary"] = summary
        narratives["distribution_conclusion"] = [
            f"本周期共纳入 {_n(total)} 条反馈/投诉记录，一级、二级、三级问题均已按标签拆分统计。",
            f"一级问题最集中的是 {_join_items(primary, 2)}；二级层面主要集中在 {_join_items(secondary, 2)}。",
            f"三级问题中 {_join_items(tertiary, 3)} 是当前最值得优先定位的高频痛点。",
        ]
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
            f"问题链路上，高频三级问题为 {_join_items(tertiary, 3)}，对应洞察维度集中在 {_join_items(insight_dimension, 3)}{avg_text}。",
            "误订购、退订困难、权益无法兑换等问题不宜只按标签看数量，应联动客户关键诉求、退费诉求、客服处理动作和典型原声判断触发原因。",
        ]
    else:
        narratives["journey_summary"] = ["当前未提取到足够的问题链路字段，无法形成稳定的归因摘要。"]
    if operation_action or latent_need:
        narratives["operation_need_summary"] = [
            f"运营举措中高频项为 {_join_items(operation_action, 3)}，相关隐性需求主要是 {_join_items(latent_need, 3)}。",
            "若运营举措对应投诉量高，应进一步拆分活动告知、权益兑现、扣费退订、赛事体验四类原因，避免只把问题归为活动咨询。",
        ]
    else:
        narratives["operation_need_summary"] = ["当前数据未提供有效运营举措或隐性需求字段，报告仅保留展示口径。"]
    if member_cluster:
        narratives["member_cluster_summary"] = [
            f"会员/业务聚类投诉最集中在 {_join_items(member_cluster, 3)}，可按会员类型拆分订购、退订、权益、赛事观看体验。",
            "会员类型维度适合产品经理判断影响面，也适合运营侧定位活动规则、权益配置和客服话术是否需要调整。",
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
            "案例阅读时建议同时看工单内容、客户关键诉求、运营举措、隐性需求和会员类型，以判断是否存在批量规则或活动解释问题。",
        ]
    else:
        narratives["case_summary"] = ["当前未提取到可展示的典型案例样本。"]
    if peak_day and neg_peak:
        narratives["trend_conclusion"] = [
            f"{peak_day['date']} 的问题量达到峰值 {_n(peak_day['count'])} 件，是当前趋势上的最高波峰。",
            f"{neg_peak['date']} 的负向情绪占比最高，为 {neg_peak.get('negative_ratio', 0) * 100:.1f}%，说明该日用户情绪最激烈。",
            _schedule_message(result),
        ]
    if anomalies:
        first = anomalies[0]
        narratives["anomaly_summary"] = [
            f"当前共识别到 {_n(len(anomalies))} 个明显异动日，其中最早的异动节点出现在 {first['date']}。",
            f"该异动日的问题量为 {_n(first['count'])} 件，日环比 {first.get('day_over_day_growth', 0) * 100:.1f}%。",
        ]
    else:
        narratives["anomaly_summary"] = ["当前周期未识别到满足阈值的明显异动日，整体波动相对平稳。"]
    return narratives


def _sanitize_lines(parsed: dict[str, Any], fallback: dict[str, list[str]]) -> dict[str, list[str]]:
    cleaned: dict[str, list[str]] = {}
    for key in NARRATIVE_KEYS:
        value = parsed.get(key)
        if isinstance(value, list):
            lines = [str(item).strip() for item in value if str(item).strip()]
            cleaned[key] = lines[:4] if lines else fallback[key]
        else:
            cleaned[key] = fallback[key]
    return cleaned


def build_report_narratives(result: dict[str, Any], llm: OpenAICompatibleClient) -> dict[str, list[str]]:
    fallback = _fallback_narratives(result)
    if not llm.enabled:
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
                "case_summary、cause_summary、voice_summary、trend_conclusion、anomaly_summary。"
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]
    response = llm.chat(messages, temperature=0.2)
    parsed = parse_json_object(response.content)
    if not parsed:
        logger.warning("Narrative builder fell back because LLM output was not valid JSON")
        return fallback
    return _sanitize_lines(parsed, fallback)
