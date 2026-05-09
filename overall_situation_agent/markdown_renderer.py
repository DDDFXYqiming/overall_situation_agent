from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .report import (
    _analysis_type_text,
    _build_trend_view,
    _distribution_insights,
    _event_label,
    _matchday,
    _matchday_note,
    _matchday_summary,
    _cause_field_summary_at,
    _narrative_line_at,
    _natural_sample_summary,
    _pct,
    _query_note_text,
    _safe_ratio,
    _selected_daily_rows,
    _source_files_text,
    _sorted_anomaly_days,
    _sum_counts,
    _trend_chart_summary,
    _trend_insights,
    _trend_voice_items,
    _trend_voice_summary,
    _unlabeled_dist_lines,
    _unlabeled_trend_lines,
)


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _md(value: Any) -> str:
    text = _text(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def _n(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return _text(value)


def _truncate(value: Any, limit: int = 160) -> str:
    text = _text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _paragraphs(lines: list[str] | None, fallback: list[str] | None = None) -> str:
    selected = [line.strip() for line in (lines or fallback or []) if str(line).strip()]
    if not selected:
        return "暂无可生成的分析内容。"
    return "\n\n".join(_text(line) for line in selected)


def _unlabeled_md_block(lines: list[str], title: str = "未标注一二三级标签工单分析") -> str:
    if not lines:
        return ""
    body = "\n\n".join(_text(line) for line in lines)
    return f"#### {title}\n\n{body}"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "暂无可展示数据。"
    header = "| " + " | ".join(_md(item) for item in headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_md(value) for value in row) + " |" for row in rows]
    return "\n".join([header, divider, *body])


def _chart_note(original: str, markdown_view: str = "数据表") -> str:
    return f"<small>原图：{original}；Markdown 展示：{markdown_view}。</small>"


def _rank_table(items: list[dict], total: int, label_name: str, limit: int = 10) -> str:
    rows = []
    for idx, item in enumerate([entry for entry in items if entry.get("count", 0) > 0][:limit], start=1):
        count = int(item.get("count", 0))
        rows.append([idx, item.get("key", "未标注"), _n(count), _pct(_safe_ratio(count, total))])
    return _table(["排名", label_name, "提及量", "占比"], rows)


def _tag_counts(items: list[dict], limit: int = 5) -> str:
    visible = [item for item in items if item.get("count", 0) > 0][:limit]
    if not visible:
        return "无"
    total = sum(int(item.get("count", 0)) for item in visible)
    parts = []
    for item in visible:
        count = int(item.get("count", 0))
        pct = f"{count / total * 100:.1f}%" if total > 0 else "0.0%"
        parts.append(f"{item.get('key', '未标注')}（共{_n(count)}条，占比{pct}）")
    return "、".join(parts)


def _key_text(items: list[Any], limit: int = 3) -> str:
    keys = []
    for item in (items or [])[:limit]:
        value = item.get("key") if isinstance(item, dict) else item
        text = str(value or "").strip()
        if text:
            keys.append(text)
    return "、".join(keys) or "无"


def _duration_text(value: Any) -> str:
    if isinstance(value, (int, float)) and not math.isnan(float(value)):
        return f"{float(value):.1f} 分钟"
    return "未覆盖"


def _maybe_tag_row(label: str, items: list[dict], limit: int = 5) -> list[Any] | None:
    if not any(item.get("count", 0) > 0 for item in items):
        return None
    return [label, _tag_counts(items, limit=limit)]


def _compact_rows(rows: list[list[Any] | None]) -> list[list[Any]]:
    return [row for row in rows if row]


def _optional_table(title: str, headers: list[str], rows: list[list[Any] | None]) -> str:
    compacted = _compact_rows(rows)
    if not compacted:
        return ""
    return f"**{title}**\n\n{_table(headers, compacted)}"


def _drilldown_markdown(items: list[dict], total: int) -> str:
    if not items:
        return "暂无可展示的标签下钻关系。"

    lines: list[str] = []
    for primary in items:
        primary_count = int(primary.get("count", 0))
        if primary_count <= 0:
            continue
        lines.append(
            f"**一级标签：{_text(primary.get('key', '未标注'))}"
            f"（{_n(primary_count)} 次，占比 {_pct(_safe_ratio(primary_count, total))}）**"
        )
        secondaries = [item for item in primary.get("secondary", []) if item.get("count", 0) > 0]
        if not secondaries:
            lines.append("  - 二级标签：无")
            lines.append("")
            continue

        for secondary in secondaries:
            secondary_count = int(secondary.get("count", 0))
            lines.append(
                f"  - 二级标签：{_text(secondary.get('key', '未标注'))}"
                f"（{_n(secondary_count)} 次，占一级 {_pct(_safe_ratio(secondary_count, primary_count))}）"
            )
            tertiaries = [item for item in secondary.get("tertiary", []) if item.get("count", 0) > 0]
            if not tertiaries:
                lines.append("    - 三级标签：无")
                continue
            for tertiary in tertiaries:
                tertiary_count = int(tertiary.get("count", 0))
                lines.append(
                    f"    - 三级标签：{_text(tertiary.get('key', '未标注'))}"
                    f"（{_n(tertiary_count)} 次，占二级 {_pct(_safe_ratio(tertiary_count, secondary_count))}）"
                )
        lines.append("")
    return "\n".join(lines).strip() or "暂无可展示的标签下钻关系。"


def _cause_table(items: list[dict]) -> str:
    rows = []
    for item in [entry for entry in items if entry.get("count", 0) > 0][:10]:
        samples = []
        for sample in item.get("samples", [])[:2]:
            excerpt = _truncate(sample.get("content_excerpt"), 120)
            if excerpt:
                samples.append(excerpt)
        rows.append(
            [
                item.get("key", "未标注"),
                _n(item.get("count", 0)),
                _tag_counts(item.get("top_appeals", []), limit=3),
                "<br>".join(samples) if samples else "无",
            ]
        )
    return _table(["三级问题", "提及量", "高频诉求", "样例摘要"], rows)


def _operation_need_table(items: list[dict]) -> str:
    rows = []
    for item in [entry for entry in items if entry.get("count", 0) > 0][:8]:
        sample = next(
            (
                _truncate(sample.get("content_excerpt"), 120)
                for sample in item.get("samples", [])[:1]
                if _text(sample.get("content_excerpt"))
            ),
            "无",
        )
        rows.append(
            [
                item.get("key", "未标注"),
                _n(item.get("count", 0)),
                _tag_counts(item.get("top_latent_needs", []), limit=2),
                _tag_counts(item.get("top_member_clusters", []), limit=2),
                _tag_counts(item.get("top_tertiary", []), limit=2),
                sample,
            ]
        )
    return _table(["运营举措", "提及量", "隐性需求", "会员类型", "相关问题", "代表样例"], rows)


def _latent_need_table(items: list[dict]) -> str:
    rows = []
    for item in [entry for entry in items if entry.get("count", 0) > 0][:8]:
        rows.append(
            [
                item.get("key", "未标注"),
                _n(item.get("count", 0)),
                _tag_counts(item.get("top_operations", []), limit=2),
                _tag_counts(item.get("top_members", []), limit=2),
            ]
        )
    return _table(["隐性需求", "提及量", "关联运营举措", "关联会员类型"], rows)


def _member_cluster_table(items: list[dict]) -> str:
    rows = []
    for item in [entry for entry in items if entry.get("count", 0) > 0][:10]:
        rows.append(
            [
                item.get("key", "未标注"),
                _n(item.get("count", 0)),
                _tag_counts(item.get("top_tertiary", []), limit=3),
                _tag_counts(item.get("top_appeals", []), limit=2),
            ]
        )
    return _table(["会员/业务类型", "提及量", "高频问题", "高频诉求"], rows)


def _case_markdown(result: dict) -> str:
    rows = []
    for item in result.get("top_tertiary_examples", [])[:3]:
        for sample in item.get("samples", [])[:1]:
            rows.append(
                [
                    item.get("key", "未标注"),
                    _n(item.get("count", 0)),
                    sample.get("appeal") or "无",
                    _truncate(sample.get("content_excerpt"), 120),
                ]
            )
    return _table(["三级问题", "关联量", "客户诉求", "样例摘要"], rows[:4])


def _merged_cause_voice_markdown(result: dict, narratives: dict[str, list[str]] | None = None) -> str:
    examples = result.get("top_tertiary_examples", [])
    if not examples:
        return ""
    narratives = narratives or {}
    rows = []
    for idx, item in enumerate(examples):
        count = int(item.get("count", 0))
        field_summary = _cause_field_summary_at(narratives, item, idx)
        rows.append(
            [
                item.get("key", "未标注"),
                f"{_n(count)}条",
                field_summary.get("content_reply_summary", ""),
                field_summary.get("appeal_keyword_summary", ""),
                field_summary.get("cs_action_keyword_summary", ""),
            ]
        )
    return _table(["三级问题", "提及量", "工单内容与客服回复总结", "客户诉求与关键词总结", "客服处理动作与关键词总结"], rows)


def _matchday_text(day: dict) -> str:
    summary = _matchday_summary(day)
    event = _event_label(day)
    if _matchday(day):
        return f"**[赛事日]** {summary}".strip()
    if event:
        return f"非赛事日；补充线索：{event}"
    return "非赛事日"


def _daily_table(days: list[dict]) -> str:
    rows = []
    for day in days:
        growth = day.get("day_over_day_growth")
        rows.append(
            [
                day.get("date"),
                _n(day.get("count", 0)),
                "首日" if growth is None else _pct(float(growth)),
                _n(day.get("negative_count", 0)),
                _pct(float(day.get("negative_ratio", 0))),
                _matchday_text(day),
                _tag_counts(day.get("top_tertiary", []), limit=3),
            ]
        )
    return _table(["日期", "问题量", "日环比", "负向情绪量", "负向占比", "赛事日", "主要三级问题"], rows)


def _anomaly_table(anomalies: list[dict]) -> str:
    if not anomalies:
        return "当前周期未识别到日环比超过 50% 且当日问题量不少于 5 件的明显异动。"
    rows = []
    for day in _sorted_anomaly_days(anomalies)[:3]:
        rows.append(
            [
                day.get("date"),
                _pct(float(day.get("day_over_day_growth", 0))),
                _pct(float(day.get("negative_ratio", 0))),
                _matchday_text(day),
                _tag_counts(day.get("top_primary", []), limit=2),
                _tag_counts(day.get("top_secondary", []), limit=2),
                _tag_counts(day.get("top_tertiary", []), limit=3),
                f"服务类型：{_tag_counts(day.get('top_service_type', []), limit=2)}；涉及业务/会员类型：{_tag_counts(day.get('top_member_cluster', []), limit=2)}",
            ]
        )
    method = (
        "以上日期基于日聚合口径，日环比增长 ≥ 50% 且当日问题量 ≥ 5 件被识别为异动。"
        "按日环比降序排列，以下列出排名前三的异动节点。"
    )
    table = _table(["日期", "日环比", "负向占比", "赛事日", "主要一级问题", "主要二级问题", "主要三级问题", "业务维度热点"], rows)
    return f"{method}\n\n{table}"


def _simple_distribution_table(title: str, items: list[dict], original_chart: str, limit: int = 10) -> str:
    total = _sum_counts(items)
    rows = []
    for idx, item in enumerate([entry for entry in items if entry.get("count", 0) > 0][:limit], start=1):
        count = int(item.get("count", 0))
        rows.append([idx, item.get("key", "未标注"), _n(count), _pct(_safe_ratio(count, total))])
    return f"#### {title}\n\n{_chart_note(original_chart)}\n\n{_table(['排名', '类型', '提及量', '占比'], rows)}"


def _trend_voice_markdown(trend_view: dict[str, Any], narratives: dict[str, list[str]]) -> str:
    items = _trend_voice_items(trend_view)
    summary = narratives.get("trend_voice_summary") or _trend_voice_summary(items)
    summary_lines = narratives.get("trend_voice_sample_summaries") or []
    blocks = [_paragraphs(summary)]
    for idx, item in enumerate(items):
        samples = item.get("samples", [])
        sample_summaries = []
        for sample in samples[:2]:
            text = sample.get("content_excerpt", "")
            if text:
                sample_summaries.append(_natural_sample_summary(text, _key_text(item.get("top_tertiary", []), 1)))
        sample_text = _narrative_line_at(summary_lines, idx) or "；".join(sample_summaries) or "暂无样例。"
        blocks.append(
            "\n".join(
                [
                    f"**{_text(item.get('date'))} 赛事日样例**",
                    f"- 问题量：{_n(item.get('count', 0))} 件",
                    f"- 负向占比：{_pct(float(item.get('negative_ratio', 0)))}",
                    f"- 赛事摘要：{_text(item.get('match_summary') or '赛事日')}",
                    f"- 主要问题：{_tag_counts(item.get('top_tertiary', []), limit=3)}",
                    f"- 样例摘要：{sample_text}",
                ]
            )
        )
    return "\n\n".join(blocks)


def render_markdown_report(result: dict, output_path: Path) -> Path:
    query = result.get("query") or {}
    section_focus = query.get("section_focus") or "full"
    trend_view = _build_trend_view(result.get("daily", []), result.get("filters", {}), result.get("anomalies", []))
    narratives: dict[str, list[str]] = result.get("narratives") or {}
    labeled_total = int(result.get("total", 0) or 0)
    total = int(result.get("total_with_unlabeled", labeled_total) or 0)
    period_start = result.get("period", {}).get("min") or result.get("filters", {}).get("start_date") or "未限定"
    period_end = result.get("period", {}).get("max") or result.get("filters", {}).get("end_date") or "未限定"
    if len(period_start) > 10:
        period_start = period_start[:10]
    if len(period_end) > 10:
        period_end = period_end[:10]
    primary_total = _sum_counts(result.get("primary", []))
    secondary_total = _sum_counts(result.get("secondary", []))
    tertiary_total = _sum_counts(result.get("tertiary", []))
    trend_window_note = (
        trend_view.get("note") or "当前按完整查询周期展示每日趋势。"
        if section_focus in {"trend", "full"}
        else "当前报告未展示 1.2 趋势章节。"
    )

    sections: list[str] = [
        "# 视频业务产品体验问题诊断报告",
        "## 一、整体情况",
        "\n".join(
            [
                f"> 数据周期：{period_start} 至 {period_end}  ",
                f"> 总工单量：{_n(total)} 件  ",
            ]
        ),
    ]

    if section_focus in {"distribution", "full"}:
        sections.extend(
            [
                "---",
                "### 1.1 问题分布概览",
                "#### 分析结论",
                _paragraphs(narratives.get("distribution_conclusion"), _distribution_insights(result)),
                _unlabeled_md_block(narratives.get("unlabeled_distribution_summary") or _unlabeled_dist_lines(result)),
                "#### 一级问题概览",
                _chart_note("一级标签类型分布饼状图"),
                _paragraphs(narratives.get("primary_overview")),
                _rank_table(result.get("primary", []), primary_total, "一级标签"),
                "#### 二级问题概览",
                _chart_note("二级标签类型分布饼状图"),
                _paragraphs(narratives.get("secondary_overview")),
                _rank_table(result.get("secondary", []), secondary_total, "二级标签"),
                "#### 三级问题概览",
                _chart_note("三级标签类型分布饼状图及 TOP5 三级问题柱状图", "数据表"),
                _paragraphs(narratives.get("tertiary_overview")),
                _rank_table(result.get("tertiary", []), tertiary_total, "三级标签"),
                "#### 三级问题原因线索、样例原声与典型案例",
                _chart_note("原因线索卡片与样例原声卡片", "合并数据表"),
                _paragraphs(narratives.get("cause_summary"), narratives.get("voice_summary")),
                _merged_cause_voice_markdown(result, narratives),
            ]
        )

    if section_focus in {"trend", "full"}:
        trend_summary = narratives.get("trend_chart_summary") or _trend_chart_summary(trend_view)
        sections.extend(
            [
                "---",
                "### 1.2 投诉趋势与异动表现",
                "#### 分析结论",
                _paragraphs(narratives.get("trend_conclusion"), _trend_insights(result, trend_view)),
                "#### 每日问题提及量与负向情绪占比",
                _chart_note(
                    "每日问题提及量与负向情绪占比双轴折线图（左轴为问题提及量柱状图，右轴为负向情绪占比折线图，赛事日标注红色竖线）",
                    "趋势描述和每日明细表",
                ),
                _paragraphs(trend_summary),
                f"**图表分析总结**：{trend_window_note}",
                "#### 赛事日样例原声",
                _chart_note("赛事日样例原声卡片", "文本摘要列表"),
                _trend_voice_markdown(trend_view, narratives),
                "#### 异动节点",
                _chart_note("异动节点卡片", "异动节点表格"),
                _paragraphs(narratives.get("anomaly_summary")),
                _anomaly_table(trend_view.get("anomalies", [])),
            ]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    return output_path
