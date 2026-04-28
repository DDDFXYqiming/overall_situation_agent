from __future__ import annotations

import re
from dataclasses import dataclass

from .llm_client import OpenAICompatibleClient, parse_json_object
from .state import AgentState


@dataclass(frozen=True)
class QueryPlan:
    question: str
    start_date: str | None = None
    end_date: str | None = None
    focus: str = "overall_situation"
    section_focus: str = "full"
    note: str = "使用规则解析生成查询计划。"
    used_llm: bool = False


DATE_PATTERN = re.compile(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?")


def _normalize_date(match: re.Match[str]) -> str:
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def fallback_plan(question: str, state: AgentState) -> QueryPlan:
    dates = [_normalize_date(match) for match in DATE_PATTERN.finditer(question)]
    start_date = dates[0] if dates else state.last_start_date
    end_date = dates[1] if len(dates) > 1 else (dates[0] if dates else state.last_end_date)
    section_focus = infer_section_focus(question)
    return QueryPlan(question=question, start_date=start_date, end_date=end_date, section_focus=section_focus)


def infer_section_focus(question: str) -> str:
    distribution_terms = ["问题分布", "类型分布", "总量", "一级", "二级", "三级", "top", "TOP", "排名", "痛点"]
    trend_terms = ["按日", "趋势", "异动", "波动", "负向情绪", "情绪指数", "赛事日", "时间节点"]
    has_distribution = any(term in question for term in distribution_terms)
    has_trend = any(term in question for term in trend_terms)
    if has_distribution and not has_trend:
        return "distribution"
    if has_trend and not has_distribution:
        return "trend"
    return "full"


def plan_query(question: str, state: AgentState, llm: OpenAICompatibleClient) -> QueryPlan:
    fallback = fallback_plan(question, state)
    if not llm.enabled:
        return fallback

    messages = [
        {
            "role": "system",
            "content": (
                "你是报告查询规划器，只输出 JSON。"
                "任务：从用户问题中提取用于生成《一、整体情况》HTML报告的查询参数。"
                "只允许输出字段：start_date、end_date、focus、section_focus、note。"
                "日期格式必须为 YYYY-MM-DD；无法判断则填 null。"
                "focus 固定为 overall_situation。不要生成HTML。"
                "section_focus 只能是 full、distribution、trend。"
                "当用户问问题分布、总量、一级/二级/三级、TOP排名时填 distribution；"
                "当用户问按日趋势、负向情绪、异动、赛事日时填 trend；"
                "当用户要求完整整体情况或同时包含分布和趋势时填 full。"
            ),
        },
        *state.compact_history(limit=6),
        {"role": "user", "content": question},
    ]
    response = llm.chat(messages)
    parsed = parse_json_object(response.content)
    if not parsed:
        return fallback

    return QueryPlan(
        question=question,
        start_date=parsed.get("start_date") or fallback.start_date,
        end_date=parsed.get("end_date") or fallback.end_date,
        focus="overall_situation",
        section_focus=parsed.get("section_focus") if parsed.get("section_focus") in {"full", "distribution", "trend"} else fallback.section_focus,
        note=str(parsed.get("note") or "使用大模型解析生成查询计划。"),
        used_llm=not response.used_fallback,
    )
