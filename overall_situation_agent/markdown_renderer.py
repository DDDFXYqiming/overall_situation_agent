from __future__ import annotations

import math
from datetime import datetime
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
    _pct,
    _query_note_text,
    _safe_ratio,
    _selected_daily_rows,
    _source_files_text,
    _sum_counts,
    _trend_chart_summary,
    _trend_insights,
    _trend_voice_items,
    _trend_voice_summary,
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
    return "、".join(f"{item.get('key', '未标注')}({_n(item.get('count', 0))})" for item in visible) or "无"


def _duration_text(value: Any) -> str:
    if isinstance(value, (int, float)) and not math.isnan(float(value)):
        return f"{float(value):.1f} 分钟"
    return "未覆盖"


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
                    sample.get("operation_action") or "无",
                    sample.get("biz_member_cluster") or "无",
                    sample.get("latent_need") or "无",
                    _truncate(sample.get("content_excerpt"), 120),
                ]
            )
    for item in result.get("operation_need_examples", [])[:2]:
        for sample in item.get("samples", [])[:1]:
            rows.append(
                [
                    item.get("key", "未标注"),
                    _n(item.get("count", 0)),
                    sample.get("appeal") or "无",
                    sample.get("operation_action") or "无",
                    sample.get("biz_member_cluster") or "无",
                    sample.get("latent_need") or "无",
                    _truncate(sample.get("content_excerpt"), 120),
                ]
            )
    return _table(["案例来源", "关联量", "诉求", "运营举措", "会员类型", "隐性需求", "样例摘要"], rows[:4])


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
    for day in anomalies:
        rows.append(
            [
                day.get("date"),
                _n(day.get("count", 0)),
                _pct(float(day.get("day_over_day_growth", 0))),
                _pct(float(day.get("negative_ratio", 0))),
                _matchday_text(day),
                _tag_counts(day.get("top_tertiary", []), limit=3),
            ]
        )
    return _table(["日期", "问题量", "日环比", "负向占比", "赛事日", "主要三级问题"], rows)


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
    blocks = [_paragraphs(summary)]
    for item in items:
        blocks.append(
            "\n".join(
                [
                    f"**{_text(item.get('date'))} 赛事日样例**",
                    f"- 问题量：{_n(item.get('count', 0))} 件",
                    f"- 负向占比：{_pct(float(item.get('negative_ratio', 0)))}",
                    f"- 赛事摘要：{_text(item.get('match_summary') or '赛事日')}",
                    f"- 主要问题：{_tag_counts(item.get('top_tertiary', []), limit=3)}",
                    *[
                        f"- 样例：{_truncate(sample.get('content_excerpt'), 140)}"
                        for sample in item.get("samples", [])[:2]
                        if _text(sample.get("content_excerpt"))
                    ],
                ]
            )
        )
    return "\n\n".join(blocks)


def render_markdown_report(result: dict, output_path: Path) -> Path:
    query = result.get("query") or {}
    section_focus = query.get("section_focus") or "full"
    trend_view = _build_trend_view(result.get("daily", []), result.get("filters", {}), result.get("anomalies", []))
    narratives: dict[str, list[str]] = result.get("narratives") or {}
    total = int(result.get("total", 0) or 0)
    period_start = result.get("period", {}).get("min") or result.get("filters", {}).get("start_date") or "未限定"
    period_end = result.get("period", {}).get("max") or result.get("filters", {}).get("end_date") or "未限定"
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
                f"> 分析类型：{_analysis_type_text(section_focus)}  ",
                f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ]
        ),
        "### 核心摘要",
        _paragraphs(narratives.get("executive_summary"), _distribution_insights(result)[:3]),
    ]

    if query.get("question") or query.get("note"):
        sections.append(
            "\n".join(
                [
                    "### 本次查询",
                    f"- 本次提问：{_text(query.get('question') or '未提供')}",
                    f"- 查询说明：{_query_note_text(query, section_focus)}",
                ]
            )
        )

    if section_focus in {"distribution", "full"}:
        sections.extend(
            [
                "---",
                "### 1.1 问题分布概览",
                "#### 分析结论",
                _paragraphs(narratives.get("distribution_conclusion"), _distribution_insights(result)),
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
                "#### 各级标签下钻关系",
                _chart_note("各级标签下钻关系复杂表格", "分层列表"),
                _drilldown_markdown(result.get("primary_secondary_tertiary", []), primary_total),
                "#### 三级问题原因线索",
                _chart_note("原因线索卡片与样例原声卡片", "简化数据表与摘要"),
                _paragraphs(narratives.get("cause_summary")),
                _cause_table(result.get("top_tertiary_examples", [])),
                "#### 样例原声与原因研判",
                _paragraphs(narratives.get("voice_summary")),
                "#### 问题链路归因",
                _paragraphs(narratives.get("journey_summary")),
                _table(
                    ["维度", "结果"],
                    [
                        ["洞察维度", _tag_counts(result.get("insight_dimension", []), limit=5)],
                        ["时段分布", _tag_counts(result.get("time_period", []), limit=5)],
                        ["省份信息", _tag_counts(result.get("province", []), limit=5)],
                        ["平均处理耗时", _duration_text(result.get("avg_duration_minutes"))],
                    ],
                ),
                "#### 运营举措与隐性诉求",
                _paragraphs(narratives.get("operation_need_summary")),
                _operation_need_table(result.get("operation_need_examples", [])),
                _latent_need_table(result.get("latent_need_examples", [])),
                "#### 会员类型聚类",
                _paragraphs(narratives.get("member_cluster_summary")),
                _member_cluster_table(result.get("member_cluster_examples", [])),
                "#### 典型案例",
                _paragraphs(narratives.get("case_summary")),
                _case_markdown(result),
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
                "#### 每日趋势分析",
                _chart_note("每日问题提及量与负向情绪占比双轴折线图", "趋势描述和每日明细表"),
                _paragraphs(trend_summary),
                f"**趋势窗口**：{trend_window_note}",
                "**每日明细表（重点日期）**：为避免长日表淹没结论，本表默认展示峰值日、负向占比最高日、明显异动日及问题量靠前日期。",
                _daily_table(_selected_daily_rows(trend_view.get("days", []), trend_view.get("anomalies", []))),
                "#### 情绪与风险分布",
                _simple_distribution_table("情绪分布", result.get("emotion", []), "情绪分布横向柱状图"),
                _simple_distribution_table("服务类型", result.get("service_type", []), "服务类型标签组"),
                _simple_distribution_table("退费诉求", result.get("refund", []), "退费诉求标签组"),
                _simple_distribution_table("升级投诉倾向", result.get("escalation", []), "升级投诉倾向标签组"),
                "#### 赛事日样例原声",
                _chart_note("赛事日样例原声卡片", "文本摘要列表"),
                _trend_voice_markdown(trend_view, narratives),
                "#### 异动节点",
                _chart_note("异动节点卡片", "异动节点表格"),
                _paragraphs(narratives.get("anomaly_summary")),
                _anomaly_table(trend_view.get("anomalies", [])),
            ]
        )

    sections.extend(
        [
            "---",
            "### 口径说明",
            _table(
                ["口径", "说明"],
                [
                    ["数据来源", f"{_source_files_text(result.get('source_files', []))} 已导入 Elasticsearch，并通过聚合查询生成。"],
                    ["适用范围", _analysis_type_text(section_focus)],
                    ["负向情绪", "当前以“愤怒、失望、焦虑、不满、烦躁”作为负向情绪集合。"],
                    ["赛事日标注", _matchday_note(result, trend_view)],
                    ["趋势窗口", trend_window_note],
                    ["多标签统计", "一级、二级、三级及业务等多值字段按分隔符拆分后聚合，因此同一工单可贡献到多个标签桶。"],
                    ["用户属性字段", "当前新增表头包含省份、服务时间、时段、处理耗时、会员类型聚类等基础信息；未包含终端型号、App 版本字段，报告不做该维度推断。"],
                ],
            ),
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    return output_path
