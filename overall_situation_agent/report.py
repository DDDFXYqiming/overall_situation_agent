from __future__ import annotations

import math
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Any

from .style_guard import enforce_style_contract

CHART_COLORS = ["#0052FF", "#4D7CFF", "#38BDF8", "#22C55E", "#F97316", "#A855F7", "#64748B", "#0F172A"]


def _e(value: Any) -> str:
    return escape("" if value is None else str(value))


def _n(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return _e(value)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _sum_counts(items: list[dict]) -> int:
    return int(sum(item.get("count", 0) for item in items))


def _safe_ratio(part: float, whole: float) -> float:
    return part / whole if whole else 0


def _tags(items: list[dict]) -> str:
    tags = []
    for item in items:
        tags.append(
            f'<span class="tag"><span class="tag-text">{_e(item["key"])}</span><strong>{_e(item["count"])}</strong></span>'
        )
    return "".join(tags)


def _bar_rows(items: list[dict], alt: bool = False) -> str:
    visible = [item for item in items if item.get("count", 0) > 0]
    if not visible:
        return '<p class="subtle">暂无可展示数据。</p>'
    max_value = max(item["count"] for item in visible) or 1
    cls = "bar-fill alt" if alt else "bar-fill"
    rows = []
    for item in visible:
        width = round(item["count"] / max_value * 100, 1) if max_value else 0
        rows.append(
            f"""
            <div class="bar-row">
              <div class="bar-label">{_e(item["key"])}</div>
              <div class="bar-track"><div class="{cls}" style="--target-width:{width}%"></div></div>
              <div class="bar-value">{_e(item["count"])}</div>
            </div>
            """
        )
    return "".join(rows)


def _polar_to_xy(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    radians = math.radians(angle - 90)
    return cx + radius * math.cos(radians), cy + radius * math.sin(radians)


def _wedge_path(cx: float, cy: float, radius: float, start_angle: float, end_angle: float) -> str:
    start_x, start_y = _polar_to_xy(cx, cy, radius, start_angle)
    end_x, end_y = _polar_to_xy(cx, cy, radius, end_angle)
    large_arc = 1 if end_angle - start_angle > 180 else 0
    return f"M {cx:.2f} {cy:.2f} L {start_x:.2f} {start_y:.2f} A {radius:.2f} {radius:.2f} 0 {large_arc} 1 {end_x:.2f} {end_y:.2f} Z"


def _donut_chart(items: list[dict], title: str, total_label: str) -> str:
    positive = [item for item in items if item.get("count", 0) > 0]
    if len(positive) > 6:
        visible = [dict(item) for item in positive[:5]]
        remainder_count = _sum_counts(positive[5:])
        other_bucket = next((item for item in visible if item.get("key") == "其他"), None)
        if other_bucket:
            other_bucket["count"] = int(other_bucket.get("count", 0)) + remainder_count
        else:
            visible.append({"key": "其他", "count": remainder_count})
    else:
        visible = positive[:6]
    total = _sum_counts(visible)
    if not visible or total == 0:
        return '<section class="chart-card" data-reveal="card"><p class="subtle">暂无可绘制的类型分布数据。</p></section>'

    cx, cy, radius = 116, 116, 88
    angle = 0.0
    slices = []
    legend = []
    for idx, item in enumerate(visible):
        color = CHART_COLORS[idx % len(CHART_COLORS)]
        share = _safe_ratio(item["count"], total)
        next_angle = angle + share * 360
        if share >= 0.999:
            slices.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{color}" />')
        else:
            slices.append(f'<path d="{_wedge_path(cx, cy, radius, angle, next_angle)}" fill="{color}" />')
        legend.append(
            f"""
            <div class="legend-row">
              <span class="legend-swatch" style="background:{color}"></span>
              <span class="legend-name">{_e(item["key"])}</span>
              <strong>{item["count"]}</strong>
              <span class="legend-share">{_pct(share)}</span>
            </div>
            """
        )
        angle = next_angle

    return f"""
    <section class="chart-card chart-card-highlight" data-reveal="card">
      <div class="chart-header">
        <div>
          <span class="chart-kicker">PIE CHART</span>
          <h3>{_e(title)}</h3>
        </div>
      </div>
      <div class="pie-layout">
        <svg class="donut-chart" viewBox="0 0 232 232" role="img" aria-label="{_e(title)}">
          {''.join(slices)}
          <circle cx="{cx}" cy="{cy}" r="50" fill="#FFFFFF" />
          <text x="{cx}" y="{cy - 3}" text-anchor="middle" class="donut-total">{total}</text>
          <text x="{cx}" y="{cy + 19}" text-anchor="middle" class="donut-caption">{_e(total_label)}</text>
        </svg>
        <div class="legend-stack">{''.join(legend)}</div>
      </div>
    </section>
    """


def _top_bar_chart(items: list[dict]) -> str:
    visible = [item for item in items[:5] if item.get("count", 0) > 0]
    if not visible:
        return '<section class="chart-card" data-reveal="card"><p class="subtle">暂无 TOP 问题数据。</p></section>'
    max_value = max(item["count"] for item in visible) or 1
    rows = []
    for idx, item in enumerate(visible, start=1):
        width = round(item["count"] / max_value * 100, 1)
        rows.append(
            f"""
            <div class="rank-row">
              <div class="rank-index">{idx:02d}</div>
              <div class="rank-label">{_e(item["key"])}</div>
              <div class="rank-track"><div class="rank-fill" style="--target-width:{width}%"></div></div>
              <div class="rank-value">{item["count"]}</div>
            </div>
            """
        )
    return f"""
    <section class="chart-card" data-reveal="card">
      <div class="chart-header">
        <div>
          <span class="chart-kicker">BAR CHART</span>
          <h3>TOP5 三级问题提及量</h3>
        </div>
      </div>
      <div class="rank-chart">{''.join(rows)}</div>
    </section>
    """


def _label_drilldown_table(items: list[dict], total: int) -> str:
    if not items:
        return '<section class="chart-card chart-grid-wide" data-reveal="card"><p class="subtle">暂无可展示的标签下钻关系。</p></section>'

    rows = []
    for primary in items:
        primary_count = int(primary.get("count", 0))
        secondaries = [item for item in primary.get("secondary", []) if item.get("count", 0) > 0]
        if not secondaries:
            rows.append(
                f"""
                <tr>
                  <td>{_e(primary["key"])}</td>
                  <td>{_n(primary_count)}</td>
                  <td>{_pct(_safe_ratio(primary_count, total))}</td>
                  <td>无</td>
                  <td>0</td>
                  <td>0.0%</td>
                  <td>无</td>
                  <td>0</td>
                  <td>0.0%</td>
                </tr>
                """
            )
            continue

        for secondary in secondaries:
            secondary_count = int(secondary.get("count", 0))
            tertiaries = [item for item in secondary.get("tertiary", []) if item.get("count", 0) > 0]
            if not tertiaries:
                rows.append(
                    f"""
                    <tr>
                      <td>{_e(primary["key"])}</td>
                      <td>{_n(primary_count)}</td>
                      <td>{_pct(_safe_ratio(primary_count, total))}</td>
                      <td>{_e(secondary["key"])}</td>
                      <td>{_n(secondary_count)}</td>
                      <td>{_pct(_safe_ratio(secondary_count, primary_count))}</td>
                      <td>无</td>
                      <td>0</td>
                      <td>0.0%</td>
                    </tr>
                    """
                )
                continue

            for tertiary in tertiaries:
                tertiary_count = int(tertiary.get("count", 0))
                rows.append(
                    f"""
                    <tr>
                      <td>{_e(primary["key"])}</td>
                      <td>{_n(primary_count)}</td>
                      <td>{_pct(_safe_ratio(primary_count, total))}</td>
                      <td>{_e(secondary["key"])}</td>
                      <td>{_n(secondary_count)}</td>
                      <td>{_pct(_safe_ratio(secondary_count, primary_count))}</td>
                      <td>{_e(tertiary["key"])}</td>
                      <td>{_n(tertiary_count)}</td>
                      <td>{_pct(_safe_ratio(tertiary_count, secondary_count))}</td>
                    </tr>
                    """
                )

    return f"""
    <section class="chart-card chart-grid-wide" data-reveal="card">
      <div class="chart-header">
        <div>
          <span class="chart-kicker">LABEL DRILLDOWN</span>
          <h3>各级标签下钻关系表</h3>
        </div>
      </div>
      <div class="narrative-stack">
        <p>按“一级标签 → 二级标签 → 三级标签”路径展开，展示每级标签在当前层级中的占比，以及它与上下级标签的对应关系。</p>
      </div>
      <div class="table-scroll">
        <table class="data-table drilldown-table">
          <thead>
            <tr>
              <th>一级标签</th>
              <th>一级提及量</th>
              <th>一级占比</th>
              <th>二级标签</th>
              <th>二级提及量</th>
              <th>二级在一级内占比</th>
              <th>三级标签</th>
              <th>三级提及量</th>
              <th>三级在二级内占比</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    </section>
    """


def _event_label(day: dict) -> str:
    events = []
    for item in day.get("top_events", []):
        key = str(item.get("key", ""))
        if key and key not in {"无", "其他", "未标注", "不适用"}:
            events.append(f"{key}({item.get('count', 0)})")
    return "、".join(events[:2])


def _matchday(day: dict) -> dict[str, Any] | None:
    if day.get("is_matchday") and day.get("matchday"):
        return day["matchday"]
    return None


def _matchday_summary(day: dict) -> str:
    payload = _matchday(day)
    if not payload:
        return ""
    return str(payload.get("match_summary", "")).strip()


def _matchday_round_text(day: dict) -> str:
    payload = _matchday(day)
    if not payload:
        return ""
    rounds = [str(item).strip() for item in payload.get("rounds", []) if str(item).strip()]
    return "、".join(rounds)


def _matchday_count(day: dict) -> int:
    payload = _matchday(day)
    return int(payload.get("match_count", 0)) if payload else 0


def _schedule_status(result: dict) -> dict[str, Any]:
    return result.get("schedule") or {"status": "missing", "message": "未提供赛程文件，1.2 未标注赛事日。", "days": {}}


def _matchday_pill(day: dict, dark: bool = False) -> str:
    if _matchday(day):
        cls = "match-pill match-pill-dark" if dark else "match-pill"
        return f'<span class="{cls}">赛事日</span>'
    cls = "match-pill match-pill-muted-dark" if dark else "match-pill match-pill-muted"
    return f'<span class="{cls}">非赛事日</span>'


def _matchday_cell(day: dict, dark: bool = False) -> str:
    summary = _matchday_summary(day)
    scene_event = _event_label(day)
    parts = [f'<div class="day-marker">', _matchday_pill(day, dark)]
    if summary:
        parts.append(f'<div class="day-marker-copy"><strong>{_e(summary)}</strong>')
        if scene_event:
            parts.append(f'<span class="day-marker-subtle">补充线索：{_e(scene_event)}</span>')
        parts.append("</div>")
    else:
        parts.append('<div class="day-marker-copy"><strong>当日未匹配到活动日历</strong>')
        if scene_event:
            parts.append(f'<span class="day-marker-subtle">补充线索：{_e(scene_event)}</span>')
        parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


def _matchday_note(result: dict, trend_view: dict[str, Any]) -> str:
    schedule = _schedule_status(result)
    if schedule.get("status") == "loaded":
        if any(_matchday(day) for day in trend_view.get("days", [])):
            return f"赛事日根据运行时传入的赛程文件《{_e(schedule.get('source_name'))}》按日期标注。"
        return f"已加载赛程文件《{_e(schedule.get('source_name'))}》，但当前趋势窗口未匹配到赛程日期。"
    return str(schedule.get("message") or "未提供赛程文件，1.2 未标注赛事日。")


def _parse_day(value: str) -> date:
    return datetime.fromisoformat(value[:10]).date()


def _nice_upper_bound(value: int) -> int:
    if value <= 0:
        return 1
    magnitude = 10 ** int(math.floor(math.log10(value)))
    normalized = value / magnitude
    if normalized <= 1:
        factor = 1
    elif normalized <= 2:
        factor = 2
    elif normalized <= 3:
        factor = 3
    elif normalized <= 4:
        factor = 4
    elif normalized <= 5:
        factor = 5
    elif normalized <= 6:
        factor = 6
    elif normalized <= 8:
        factor = 8
    else:
        factor = 10
    return int(factor * magnitude)


def _build_trend_view(daily: list[dict], filters: dict | None = None, anomalies: list[dict] | None = None) -> dict[str, Any]:
    anomalies = anomalies or []
    if not daily:
        return {
            "days": [],
            "anomalies": [],
            "used_focus_window": False,
            "start": None,
            "end": None,
            "trimmed_count": 0,
            "trimmed_active_days": 0,
            "note": "",
        }

    filters = filters or {}
    if filters.get("start_date") or filters.get("end_date"):
        return {
            "days": daily,
            "anomalies": anomalies,
            "used_focus_window": False,
            "start": daily[0]["date"],
            "end": daily[-1]["date"],
            "trimmed_count": 0,
            "trimmed_active_days": 0,
            "note": "当前按用户指定的完整查询周期展示每日趋势。",
        }

    active_entries = [(index, day, _parse_day(day["date"])) for index, day in enumerate(daily) if day.get("count", 0) > 0]
    if len(active_entries) <= 1:
        return {
            "days": daily,
            "anomalies": anomalies,
            "used_focus_window": False,
            "start": daily[0]["date"],
            "end": daily[-1]["date"],
            "trimmed_count": 0,
            "trimmed_active_days": 0,
            "note": "当前按完整查询周期展示每日趋势。",
        }

    segments: list[dict[str, Any]] = []
    current = {
        "start_index": active_entries[0][0],
        "end_index": active_entries[0][0],
        "start_date": active_entries[0][1]["date"],
        "end_date": active_entries[0][1]["date"],
        "total_count": active_entries[0][1]["count"],
        "active_days": 1,
    }
    previous_date = active_entries[0][2]

    for index, day, current_date in active_entries[1:]:
        if (current_date - previous_date).days > 14:
            segments.append(current)
            current = {
                "start_index": index,
                "end_index": index,
                "start_date": day["date"],
                "end_date": day["date"],
                "total_count": day["count"],
                "active_days": 1,
            }
        else:
            current["end_index"] = index
            current["end_date"] = day["date"]
            current["total_count"] += day["count"]
            current["active_days"] += 1
        previous_date = current_date
    segments.append(current)

    if len(segments) == 1:
        return {
            "days": daily,
            "anomalies": anomalies,
            "used_focus_window": False,
            "start": daily[0]["date"],
            "end": daily[-1]["date"],
            "trimmed_count": 0,
            "trimmed_active_days": 0,
            "note": "当前按完整查询周期展示每日趋势。",
        }

    total_count = sum(day.get("count", 0) for day in daily)
    active_total = sum(1 for day in daily if day.get("count", 0) > 0)
    dominant = max(segments, key=lambda item: (item["total_count"], item["active_days"]))
    trimmed_count = total_count - int(dominant["total_count"])
    trimmed_active_days = active_total - int(dominant["active_days"])
    dominant_span = int(dominant["end_index"]) - int(dominant["start_index"]) + 1

    if total_count == 0 or trimmed_count <= 0 or dominant["total_count"] / total_count < 0.85 or dominant_span >= len(daily) * 0.85:
        return {
            "days": daily,
            "anomalies": anomalies,
            "used_focus_window": False,
            "start": daily[0]["date"],
            "end": daily[-1]["date"],
            "trimmed_count": 0,
            "trimmed_active_days": 0,
            "note": "当前按完整查询周期展示每日趋势。",
        }

    view_days = daily[int(dominant["start_index"]) : int(dominant["end_index"]) + 1]
    start_date = view_days[0]["date"]
    end_date = view_days[-1]["date"]
    view_anomalies = [day for day in anomalies if start_date <= day["date"] <= end_date]
    return {
        "days": view_days,
        "anomalies": view_anomalies,
        "used_focus_window": True,
        "start": start_date,
        "end": end_date,
        "trimmed_count": trimmed_count,
        "trimmed_active_days": trimmed_active_days,
        "note": (
            f"图表聚焦主分析时段 {start_date} 至 {end_date}；未绘制此前 {trimmed_active_days} 个零散活跃日"
            f"（共 {trimmed_count} 件），避免稀疏历史点压缩当前趋势。"
        ),
    }


def _source_files_text(items: list[dict]) -> str:
    names = [str(item.get("key", "")).strip() for item in items if str(item.get("key", "")).strip()]
    return "、".join(names) if names else "当前导入的已打标工单数据"


def _trend_svg(daily: list[dict], focus_note: str | None = None) -> str:
    if not daily:
        return '<section class="chart-card" data-reveal="card"><p class="subtle">暂无趋势数据。</p></section>'

    width, height = 1120, 460
    left, right, top, bottom = 74, 92, 58, 90
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_count = max(day["count"] for day in daily) or 1
    count_axis_max = _nice_upper_bound(max_count)
    denom = len(daily) - 1 if len(daily) > 1 else 1

    def x_at(index: int) -> float:
        return left + index * plot_w / denom

    def y_count(value: float) -> float:
        return top + (1 - value / count_axis_max) * plot_h

    def y_ratio(value: float) -> float:
        return top + (1 - value) * plot_h

    count_points = [(x_at(i), y_count(day["count"])) for i, day in enumerate(daily)]
    ratio_points = [(x_at(i), y_ratio(day["negative_ratio"])) for i, day in enumerate(daily)]
    count_path = " ".join(f"{x:.1f},{y:.1f}" for x, y in count_points)
    ratio_path = " ".join(f"{x:.1f},{y:.1f}" for x, y in ratio_points)

    grid_lines = []
    for i in range(5):
        y = top + i * plot_h / 4
        count_tick = int(round(count_axis_max * (1 - i / 4)))
        ratio_tick = 1 - i / 4
        grid_lines.append(
            f"""
            <line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="rgba(15,23,42,0.09)" />
            <text x="{left - 14}" y="{y + 4:.1f}" text-anchor="end" class="axis-tick">{count_tick}</text>
            <text x="{width - right + 14}" y="{y + 4:.1f}" class="axis-tick">{ratio_tick:.2f}</text>
            """
        )

    x_labels = []
    event_marks = []
    point_marks = []
    label_step = max(1, math.ceil(len(daily) / 8))
    event_candidates = [(idx, day) for idx, day in enumerate(daily) if day.get("count", 0) > 0 and _matchday(day)]
    if len(event_candidates) > 8:
        event_candidates = sorted(event_candidates, key=lambda item: item[1].get("count", 0), reverse=True)[:8]
        event_candidates.sort(key=lambda item: item[0])
    event_index_set = {idx for idx, _ in event_candidates}

    peak = max(daily, key=lambda item: item["count"])
    peak_idx = daily.index(peak)
    marker_step = max(1, len(daily) // 24)
    marker_indices = set(range(0, len(daily), marker_step))
    marker_indices.update({0, len(daily) - 1, peak_idx})
    marker_indices.update(event_index_set)
    event_summary = []

    for idx, day in enumerate(daily):
        x = x_at(idx)
        if idx % label_step == 0 or idx == len(daily) - 1:
            x_labels.append(f'<text x="{x:.1f}" y="{height - 34}" text-anchor="middle" class="axis-tick">{_e(day["date"][5:])}</text>')

        if idx in marker_indices:
            cx, cy = count_points[idx]
            rx, ry = ratio_points[idx]
            outer_circle = ""
            if day.get("day_over_day_growth", 0) >= 0.5 and _matchday(day):
                outer_circle = f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" fill="none" stroke="#9EB6FF" stroke-width="2" />'
            point_marks.append(
                f"""
                {outer_circle}
                <circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.6" fill="#4D7CFF" />
                <circle cx="{rx:.1f}" cy="{ry:.1f}" r="4.6" fill="#F97316" />
                """
            )

        if idx in event_index_set:
            event = _matchday_summary(day)
            highlight_cls = "event-pill event-pill-strong"
            if day["date"] == peak["date"]:
                highlight_cls += " event-pill-peak"
            event_summary.append(
                f'<span class="{highlight_cls}"><strong>{_e(day["date"][5:])}</strong><span>{_e(event)}</span></span>'
            )
            event_marks.append(
                f"""
                <line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height - bottom}" stroke="rgba(77,124,255,0.46)" stroke-dasharray="4 7" />
                """
            )

    peak_x, peak_y = count_points[peak_idx]
    peak_box_width = 168
    peak_box_x = min(max(peak_x + 14, left + 10), width - right - peak_box_width)
    peak_box_y = max(16, peak_y - 48)
    peak_box_fill = "rgba(0,82,255,0.10)" if _matchday(peak) else "rgba(255,255,255,0.92)"
    peak_box_stroke = "rgba(0,82,255,0.34)" if _matchday(peak) else "rgba(15,23,42,0.08)"
    peak_text = f"峰值 {peak['date'][5:]} | {peak['count']} 件"
    if _matchday(peak):
        peak_text += " | 赛事日"
    focus_note_html = f'<p class="trend-note">{_e(focus_note)}</p>' if focus_note else ""

    return f"""
    <section class="chart-card chart-card-highlight" data-reveal="card">
      <div class="chart-header">
        <div>
          <span class="chart-kicker">LINE CHART</span>
          <h3>每日问题提及量与负向情绪占比</h3>
        </div>
      </div>
      <svg class="trend-svg" viewBox="0 0 {width} {height}" role="img" aria-label="每日问题提及量与负向情绪占比折线图">
        <defs>
          <linearGradient id="countGlow" x1="0%" x2="100%">
            <stop offset="0%" stop-color="#0052FF" />
            <stop offset="100%" stop-color="#4D7CFF" />
          </linearGradient>
          <linearGradient id="ratioGlow" x1="0%" x2="100%">
            <stop offset="0%" stop-color="#F97316" />
            <stop offset="100%" stop-color="#FDBA74" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="{width}" height="{height}" rx="8" fill="#FFFFFF" stroke="rgba(15,23,42,0.08)" />
        {''.join(grid_lines)}
        <line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="rgba(15,23,42,0.14)" />
        <line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="rgba(15,23,42,0.14)" />
        <line x1="{width - right}" y1="{top}" x2="{width - right}" y2="{height - bottom}" stroke="rgba(15,23,42,0.14)" />
        {''.join(event_marks)}
        <polyline points="{count_path}" fill="none" stroke="url(#countGlow)" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round" />
        <polyline points="{ratio_path}" fill="none" stroke="url(#ratioGlow)" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round" />
        {''.join(point_marks)}
        <g>
          <rect x="{peak_box_x:.1f}" y="{peak_box_y:.1f}" width="{peak_box_width}" height="32" rx="8" fill="{peak_box_fill}" stroke="{peak_box_stroke}" />
          <text x="{peak_box_x + peak_box_width / 2:.1f}" y="{peak_box_y + 21:.1f}" text-anchor="middle" fill="#0F172A" font-size="13">{_e(peak_text)}</text>
        </g>
        {''.join(x_labels)}
        <text x="{left}" y="30" class="axis-title">问题量</text>
        <text x="{width - right}" y="30" text-anchor="end" class="axis-title">负向情绪占比</text>
      </svg>
      <div class="legend">
        <span><i class="dot count"></i>问题量</span>
        <span><i class="dot negative"></i>负向情绪占比（替代指数）</span>
        <span><i class="dot event"></i>赛事日</span>
      </div>
      <div class="event-summary">{''.join(event_summary) if event_summary else '<span class="subtle">当前周期未匹配到可标注的赛事日。</span>'}</div>
      {focus_note_html}
    </section>
    """


def _daily_rows(daily: list[dict]) -> str:
    rows = []
    for day in daily:
        growth = day.get("day_over_day_growth")
        growth_text = "首日" if growth is None else _pct(growth)
        rows.append(
            f"""
            <tr>
              <td>{_e(day["date"])}</td>
              <td>{day["count"]}</td>
              <td>{growth_text}</td>
              <td>{day["negative_count"]}</td>
              <td>{_pct(day["negative_ratio"])}</td>
              <td>{_matchday_cell(day)}</td>
              <td>{_tags(day.get("top_tertiary", []))}</td>
            </tr>
            """
        )
    return "".join(rows)


def _anomaly_cards(anomalies: list[dict]) -> str:
    if not anomalies:
        return '<div class="analysis-box" data-reveal="card"><strong>异动判断</strong><p>当前周期未识别到日环比超过 50% 且当日问题量不少于 5 件的明显异动。</p></div>'
    cards = []
    for day in anomalies:
        cards.append(
            f"""
            <article class="signal-card" data-reveal="item">
              <div class="signal-card-head">
                <strong>{_e(day["date"])}</strong>
                <span class="signal-chip">日环比 { _pct(day.get("day_over_day_growth", 0)) }</span>
              </div>
              <p>问题量 {day["count"]}，负向占比 {_pct(day["negative_ratio"])}</p>
              <div class="signal-meta">
                <div><span>赛事日标注</span><p>{_matchday_pill(day)} {_e(_matchday_summary(day) or '')}</p></div>
                <div><span>主要问题</span><p>{"、".join(item["key"] for item in day.get("top_tertiary", [])) or '无'}</p></div>
              </div>
              <p class="signal-note">{_e('补充线索：' + _event_label(day) if _event_label(day) else '补充线索：无')}</p>
            </article>
            """
        )
    return f'<div class="signal-grid">{"".join(cards)}</div>'


def _primary_secondary_cards(items: list[dict], total: int) -> str:
    cards = []
    for item in items:
        cards.append(
            f"""
            <article class="detail-card" data-reveal="item">
              <div class="detail-head">
                <div>
                  <h4>{_e(item["key"])}</h4>
                  <p>提及 {item["count"]} 次，占比 {_pct(_safe_ratio(item["count"], total))}</p>
                </div>
                <span class="detail-count">{item["count"]}</span>
              </div>
              <div class="chip-cloud">{_tags(item.get("secondary", []))}</div>
            </article>
            """
        )
    return "".join(cards)


def _cause_cards(items: list[dict], total: int) -> str:
    cards = []
    for item in items:
        cards.append(
            f"""
            <article class="detail-card" data-reveal="item">
              <div class="detail-head">
                <div>
                  <h4>{_e(item["key"])}</h4>
                  <p>提及 {item["count"]} 次，占比 {_pct(_safe_ratio(item["count"], total))}</p>
                </div>
                <span class="detail-count">{item["count"]}</span>
              </div>
              <div class="chip-cloud">{_tags(item.get("top_appeals", []))}</div>
            </article>
            """
        )
    return "".join(cards)


def _voice_cards(items: list[dict]) -> str:
    cards = []
    for item in items:
        quotes = "".join(f'<div class="quote">{_e(sample.get("content_excerpt", ""))}</div>' for sample in item.get("samples", []))
        cards.append(
            f"""
            <article class="voice-card" data-reveal="item">
              <div class="voice-head">
                <h4>{_e(item["key"])}</h4>
                <span>{item["count"]} 次</span>
              </div>
              <div class="chip-cloud">{_tags(item.get("top_appeals", []))}</div>
              <div class="voice-body">{quotes}</div>
            </article>
            """
        )
    return "".join(cards)


def _overview_table(title: str, kicker: str, items: list[dict], total: int, summary: str | list[str]) -> str:
    visible = [item for item in items if item.get("count", 0) > 0][:3]
    highlights = "".join(
        f'<span class="metric-pill"><strong>{_e(item["key"])}</strong><span>{_n(item["count"])}</span></span>'
        for item in visible
    )
    summary_html = _narrative_stack(summary if isinstance(summary, list) else [summary])
    return f"""
    <section class="chart-card" data-reveal="card">
      <div class="chart-header">
        <div>
          <span class="chart-kicker">{_e(kicker)}</span>
          <h3>{_e(title)}</h3>
        </div>
      </div>
      {summary_html}
      <div class="metric-pill-row">{highlights or '<span class="subtle">暂无可展示数据。</span>'}</div>
    </section>
    """


def _narrative_stack(lines: list[str], dark: bool = False) -> str:
    cls = "narrative-stack narrative-stack-dark" if dark else "narrative-stack"
    if not lines:
        return f'<div class="{cls}"><p>暂无可生成的分析内容。</p></div>'
    return f'<div class="{cls}">{"".join(f"<p>{_e(line)}</p>" for line in lines)}</div>'


def _selected_daily_rows(days: list[dict], anomalies: list[dict] | None = None, limit: int = 12) -> list[dict]:
    if len(days) <= limit:
        return days
    selected_dates: set[str] = set()
    selected: list[dict] = []
    days_by_date = {day.get("date"): day for day in days if day.get("date")}

    def add(day: dict | None) -> None:
        if not day:
            return
        date = day.get("date")
        if not date or date in selected_dates:
            return
        selected_dates.add(date)
        selected.append(day)

    add(max(days, key=lambda item: item.get("count", 0), default=None))
    add(max(days, key=lambda item: item.get("negative_ratio", 0), default=None))
    for anomaly in anomalies or []:
        add(days_by_date.get(anomaly.get("date")) or anomaly)
    for day in sorted(days, key=lambda item: item.get("count", 0), reverse=True):
        add(day)
        if len(selected) >= limit:
            break
    return sorted(selected[:limit], key=lambda item: str(item.get("date", "")))


def _tag_text(items: list[dict], limit: int = 3) -> str:
    visible = [item for item in items if item.get("count", 0) > 0][:limit]
    return "、".join(f"{item.get('key', '未标注')}（{_n(item.get('count', 0))}）" for item in visible) or "无"


def _simple_table(headers: list[str], rows: list[list[Any]], empty_text: str = "暂无可展示数据。") -> str:
    if not rows:
        return f'<p class="subtle">{_e(empty_text)}</p>'
    header_html = "".join(f"<th>{_e(header)}</th>" for header in headers)
    rows_html = "".join(
        "<tr>" + "".join(f"<td>{_e(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"""
    <div class="table-scroll">
      <table class="data-table">
        <thead><tr>{header_html}</tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """


def _summary_card(title: str, kicker: str, lines: list[str], items: list[dict]) -> str:
    return f"""
    <section class="chart-card" data-reveal="card">
      <div class="chart-header">
        <div>
          <span class="chart-kicker">{_e(kicker)}</span>
          <h3>{_e(title)}</h3>
        </div>
      </div>
      {_narrative_stack(lines)}
      <div class="chip-cloud">{_tags(items) or '<span class="subtle">暂无可展示数据。</span>'}</div>
    </section>
    """


def _executive_summary_section(result: dict, narratives: dict[str, list[str]], trend_view: dict[str, Any]) -> str:
    lines = narratives.get("executive_summary") or _distribution_insights(result)[:3]
    peak = max(trend_view.get("days", []), key=lambda item: item.get("count", 0), default=None)
    peak_items = peak.get("top_tertiary", []) if peak else []
    return f"""
    <section class="report-section" data-reveal="section" data-lazy="section">
      <div class="section-label"><span class="pulse-dot"></span><strong>SUMMARY</strong></div>
      <div class="section-heading">
        <div>
          <h2>核心摘要</h2>
          <p>把领导关注的核心问题、风险诉求、运营举措、会员聚类和异动节点前置，便于第一眼判断本报告重点。</p>
        </div>
      </div>
      <div class="analysis-box analysis-box-gradient" data-reveal="card">
        <div class="analysis-header">
          <span class="chart-kicker">KEY TAKEAWAYS</span>
          <h3>先看结论</h3>
        </div>
        {_narrative_stack(lines)}
      </div>
      <div class="grid chart-grid">
        {_summary_card("核心问题链路", "ISSUE CHAIN", narratives.get("journey_summary") or [], result.get("tertiary", [])[:5])}
        {_summary_card("运营举措与隐性诉求", "OPERATION & NEED", narratives.get("operation_need_summary") or [], result.get("operation_action", [])[:5])}
        {_summary_card("会员类型聚类", "MEMBER CLUSTER", narratives.get("member_cluster_summary") or [], result.get("biz_member_cluster", [])[:5])}
        {_summary_card("峰值与异动节点", "PEAK & ANOMALY", _trend_insights(result, trend_view)[:2], peak_items)}
      </div>
    </section>
    """


def _operation_need_table(items: list[dict]) -> str:
    rows = []
    for item in [entry for entry in items if entry.get("count", 0) > 0][:8]:
        samples = "；".join(
            sample.get("content_excerpt", "")
            for sample in item.get("samples", [])[:1]
            if sample.get("content_excerpt")
        )
        rows.append(
            [
                item.get("key", "未标注"),
                _n(item.get("count", 0)),
                _tag_text(item.get("top_latent_needs", []), 2),
                _tag_text(item.get("top_member_clusters", []), 2),
                _tag_text(item.get("top_tertiary", []), 2),
                samples or "无",
            ]
        )
    return _simple_table(["运营举措", "提及量", "隐性需求", "会员类型", "相关问题", "代表样例"], rows)


def _member_cluster_table(items: list[dict]) -> str:
    rows = []
    for item in [entry for entry in items if entry.get("count", 0) > 0][:10]:
        rows.append(
            [
                item.get("key", "未标注"),
                _n(item.get("count", 0)),
                _tag_text(item.get("top_tertiary", []), 3),
                _tag_text(item.get("top_appeals", []), 2),
            ]
        )
    return _simple_table(["会员/业务类型", "提及量", "高频问题", "高频诉求"], rows)


def _latent_need_table(items: list[dict]) -> str:
    rows = []
    for item in [entry for entry in items if entry.get("count", 0) > 0][:8]:
        rows.append(
            [
                item.get("key", "未标注"),
                _n(item.get("count", 0)),
                _tag_text(item.get("top_operations", []), 2),
                _tag_text(item.get("top_members", []), 2),
            ]
        )
    return _simple_table(["隐性需求", "提及量", "关联运营举措", "关联会员类型"], rows)


def _case_cards(result: dict) -> str:
    cases: list[dict[str, Any]] = []
    for item in result.get("top_tertiary_examples", [])[:3]:
        for sample in item.get("samples", [])[:1]:
            cases.append(
                {
                    "title": item.get("key", "典型问题"),
                    "count": item.get("count", 0),
                    "content": sample.get("content_excerpt", ""),
                    "meta": [
                        sample.get("appeal"),
                        sample.get("operation_action"),
                        sample.get("biz_member_cluster"),
                        sample.get("latent_need"),
                    ],
                }
            )
    for item in result.get("operation_need_examples", [])[:2]:
        for sample in item.get("samples", [])[:1]:
            cases.append(
                {
                    "title": item.get("key", "运营举措"),
                    "count": item.get("count", 0),
                    "content": sample.get("content_excerpt", ""),
                    "meta": [
                        sample.get("appeal"),
                        sample.get("latent_need"),
                        sample.get("biz_member_cluster"),
                    ],
                }
            )
    if not cases:
        return '<p class="subtle">当前未提取到可展示的典型案例。</p>'
    cards = []
    for item in cases[:4]:
        meta_items = [{"key": value, "count": ""} for value in item.get("meta", []) if value]
        cards.append(
            f"""
            <article class="voice-card" data-reveal="item">
              <div class="voice-head">
                <h4>{_e(item.get("title", "典型案例"))}</h4>
                <span>{_n(item.get("count", 0))} 次</span>
              </div>
              <div class="chip-cloud">{_tags(meta_items) or '<span class="subtle">暂无补充标签。</span>'}</div>
              <div class="voice-body"><div class="quote">{_e(item.get("content") or "样例内容为空。")}</div></div>
            </article>
            """
        )
    return f'<div class="voice-grid">{"".join(cards)}</div>'


def _supporting_quotes(items: list[dict], limit: int = 3) -> str:
    blocks = []
    for item in items[:limit]:
        if not item.get("samples"):
            continue
        blocks.append(
            f"""
            <article class="voice-card" data-reveal="item">
              <div class="voice-head">
                <h4>{_e(item["key"])}</h4>
                <span>{_n(item["count"])} 次</span>
              </div>
              <div class="voice-body">
                {''.join(f'<div class="quote">{_e(sample.get("content_excerpt", ""))}</div>' for sample in item.get("samples", [])[:2])}
              </div>
            </article>
            """
        )
    return "".join(blocks)


def _compact_anomaly_cards(anomalies: list[dict]) -> str:
    if not anomalies:
        return '<div class="analysis-box" data-reveal="card"><strong>异动判断</strong><p>当前周期未识别到日环比超过 50% 且当日问题量不少于 5 件的明显异动。</p></div>'
    rows = []
    for day in anomalies[:3]:
        rows.append(
            f"""
            <article class="signal-card signal-card-compact" data-reveal="item">
              <div class="signal-card-head">
                <strong>{_e(day["date"])}</strong>
                <span class="signal-chip">日环比 {_pct(day.get("day_over_day_growth", 0))}</span>
              </div>
              <p>{_matchday_summary(day) or '非赛事日'}；问题量 {_n(day["count"])} 件；主要问题：{"、".join(item["key"] for item in day.get("top_tertiary", [])[:2]) or '无'}。</p>
            </article>
            """
        )
    return f'<div class="signal-grid">{"".join(rows)}</div>'


def _trend_chart_summary(trend_view: dict[str, Any]) -> list[str]:
    days = trend_view.get("days", [])
    if not days:
        return ["当前筛选周期内没有可绘制的趋势图数据。"]

    peak = max(days, key=lambda item: item.get("count", 0))
    negative_peak = max(days, key=lambda item: item.get("negative_ratio", 0))
    matchdays = [day for day in days if _matchday(day)]
    non_matchdays = [day for day in days if not _matchday(day)]
    anomalies = trend_view.get("anomalies", [])

    lines = [
        f"折线图显示问题量峰值出现在 {peak['date']}，当日提及 {_n(peak['count'])} 件，主要问题集中在 {'、'.join(item['key'] for item in peak.get('top_tertiary', [])[:3]) or '无'}。",
        f"负向情绪占比最高日为 {negative_peak['date']}，占比 {_pct(negative_peak.get('negative_ratio', 0))}；该指标用于替代模板中的负向情绪指数。",
    ]

    if matchdays and non_matchdays:
        matchday_avg = sum(day.get("count", 0) for day in matchdays) / len(matchdays)
        non_matchday_avg = sum(day.get("count", 0) for day in non_matchdays) / len(non_matchdays)
        lines.append(
            f"赛事日日均问题量约为 {matchday_avg:.1f} 件，非赛事日日均约为 {non_matchday_avg:.1f} 件，便于对比赛程节点是否放大投诉波动。"
        )

    if anomalies:
        strongest = max(anomalies, key=lambda item: item.get("day_over_day_growth", 0))
        lines.append(
            f"异动中增幅最高的节点为 {strongest['date']}，日环比 {_pct(strongest.get('day_over_day_growth', 0))}，需要结合赛事安排和处理动作复盘。"
        )

    return lines


def _trend_voice_items(trend_view: dict[str, Any], limit: int = 3) -> list[dict]:
    days = trend_view.get("days", [])
    if not days:
        return []

    anomaly_dates = {item["date"] for item in trend_view.get("anomalies", [])}
    peak = max(days, key=lambda item: item.get("count", 0), default=None)
    peak_date = peak.get("date") if peak else None

    matchday_samples = [day for day in days if _matchday(day) and day.get("samples")]
    matchday_samples.sort(
        key=lambda item: (
            item.get("date") == peak_date,
            item.get("date") in anomaly_dates,
            item.get("count", 0),
            item.get("negative_ratio", 0),
        ),
        reverse=True,
    )

    selected = []
    seen_dates: set[str] = set()
    for day in matchday_samples:
        if day["date"] in seen_dates:
            continue
        seen_dates.add(day["date"])
        selected.append(
            {
                "date": day["date"],
                "count": day.get("count", 0),
                "negative_ratio": day.get("negative_ratio", 0),
                "match_summary": _matchday_summary(day),
                "top_tertiary": day.get("top_tertiary", []),
                "samples": day.get("samples", [])[:2],
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _trend_voice_summary(items: list[dict]) -> list[str]:
    if not items:
        return ["当前趋势窗口内未提取到带赛事日标注的样例原声。"]

    lead = items[0]
    lead_issues = "、".join(item.get("key", "") for item in lead.get("top_tertiary", [])[:3] if item.get("key")) or "无"
    lines = [
        f"赛事日样例中，{lead['date']} 的投诉最集中，共 {_n(lead['count'])} 件；相关原声主要围绕 {lead_issues} 展开。",
        "从赛事日原声看，用户更容易在比赛前后集中反馈退订、权益兑换、订购失败和覆盖范围等即时体验问题。",
    ]
    if any(item.get("negative_ratio", 0) > 0.3 for item in items):
        high = max(items, key=lambda item: item.get("negative_ratio", 0))
        lines.append(f"{high['date']} 的负向占比达到 {_pct(high.get('negative_ratio', 0))}，说明赛事节点附近更容易出现高情绪强度投诉。")
    return lines


def _trend_voice_cards(items: list[dict]) -> str:
    if not items:
        return '<div class="analysis-box" data-reveal="card"><strong>样例原声</strong><p>当前趋势窗口内未提取到带赛事日标注的样例原声。</p></div>'

    cards = []
    for item in items:
        quotes = "".join(f'<div class="quote">{_e(sample.get("content_excerpt", ""))}</div>' for sample in item.get("samples", []))
        issue_tags = _tags(item.get("top_tertiary", []))
        cards.append(
            f"""
            <article class="voice-card" data-reveal="item">
              <div class="voice-head">
                <div>
                  <h4>{_e(item["date"])} 赛事日样例</h4>
                  <p class="voice-meta">{_e(item.get("match_summary") or '赛事日')}；问题量 {_n(item.get("count", 0))} 件；负向占比 {_pct(item.get("negative_ratio", 0))}。</p>
                </div>
                <span>{_n(item.get("count", 0))} 次</span>
              </div>
              <div class="chip-cloud">{issue_tags or '<span class="subtle">暂无主要问题标签。</span>'}</div>
              <div class="voice-body">{quotes}</div>
            </article>
            """
        )
    return f'<div class="voice-grid">{"".join(cards)}</div>'


def _legacy_overview_table(title: str, kicker: str, items: list[dict], total: int, summary: str) -> str:
    visible = [item for item in items if item.get("count", 0) > 0][:10]
    if not visible:
        body = '<p class="subtle">暂无可展示数据。</p>'
    else:
        rows = []
        for idx, item in enumerate(visible, start=1):
            rows.append(
                f"""
                <tr>
                  <td>{idx:02d}</td>
                  <td>{_e(item["key"])}</td>
                  <td>{_n(item["count"])}</td>
                  <td>{_pct(_safe_ratio(item["count"], total))}</td>
                </tr>
                """
            )
        body = f"""
        <div class="table-scroll">
          <table class="data-table level-table">
            <thead>
              <tr><th>排名</th><th>问题标签</th><th>提及量</th><th>占比</th></tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
          </table>
        </div>
        """

    return f"""
    <section class="chart-card" data-reveal="card">
      <div class="chart-header">
        <div>
          <span class="chart-kicker">{_e(kicker)}</span>
          <h3>{_e(title)}</h3>
        </div>
      </div>
      <p class="module-summary">{_e(summary)}</p>
      {body}
    </section>
    """


def _distribution_insights(result: dict) -> list[str]:
    total = result.get("total", 0)
    primary = result.get("primary", [])
    secondary = result.get("secondary", [])
    tertiary = result.get("tertiary", [])
    primary_total = _sum_counts(primary)
    secondary_total = _sum_counts(secondary)
    tertiary_total = _sum_counts(tertiary)
    insights = []
    if not total:
        return ["当前筛选周期内未检索到可统计的工单数据。"]
    if primary:
        top = primary[0]
        insights.append(
            f"本周期纳入 {total} 条反馈/投诉记录；一级问题中「{top['key']}」提及 {top['count']} 次，占一级标签提及量的 {_pct(_safe_ratio(top['count'], primary_total))}。"
        )
    if secondary:
        top_secondary = secondary[0]
        insights.append(
            f"二级问题中「{top_secondary['key']}」提及 {_n(top_secondary['count'])} 次，占二级标签提及量的 {_pct(_safe_ratio(top_secondary['count'], secondary_total))}。"
        )
    if tertiary:
        top5_count = _sum_counts(tertiary[:5])
        insights.append(
            f"三级问题 TOP5 累计提及 {top5_count} 次，占三级标签提及量的 {_pct(_safe_ratio(top5_count, tertiary_total))}；首要痛点为「{tertiary[0]['key']}」。"
        )
    refund_yes = next((item["count"] for item in result.get("refund", []) if item["key"] == "是"), 0)
    escalation_yes = next((item["count"] for item in result.get("escalation", []) if item["key"] == "是"), 0)
    insights.append(f"风险信号方面，退费诉求 {refund_yes} 件、升级投诉倾向 {escalation_yes} 件，建议与 TOP 问题联动定位影响面。")
    return insights


def _trend_insights(result: dict, trend_view: dict[str, Any]) -> list[str]:
    daily = trend_view.get("days", [])
    anomalies = trend_view.get("anomalies", [])
    if not daily:
        return ["当前筛选周期内没有可绘制的每日趋势数据。"]
    peak = max(daily, key=lambda item: item["count"])
    neg_peak = max(daily, key=lambda item: item["negative_ratio"])
    peak_match = _matchday_summary(peak)
    neg_peak_match = _matchday_summary(neg_peak)
    insights = [
        (
            f"{peak['date']} 问题提及量达到峰值 {peak['count']} 件"
            f"{'，该日为' + peak_match if peak_match else ''}，主要问题为："
            f"{'、'.join(item['key'] for item in peak.get('top_tertiary', [])) or '无'}。"
        ),
        (
            f"{neg_peak['date']} 负向情绪占比最高，为 {_pct(neg_peak['negative_ratio'])}"
            f"{'，该日为' + neg_peak_match if neg_peak_match else ''}；"
            "当前以负向占比替代模板中的负向情绪指数。"
        ),
    ]
    if anomalies:
        first = anomalies[0]
        match_note = _matchday_summary(first)
        insights.append(
            f"识别到 {len(anomalies)} 个明显异动日，首个异动日为 {first['date']}"
            f"{'，该日为' + match_note if match_note else ''}，日环比 {_pct(first.get('day_over_day_growth', 0))}。"
        )
    else:
        insights.append("未发现日环比超过 50% 且当日问题量不少于 5 件的明显异动日，整体波动相对平稳。")
    if trend_view.get("used_focus_window"):
        insights.append(
            f"为保证折线图可读性，1.2 图表聚焦主分析时段 {trend_view['start']} 至 {trend_view['end']}；"
            f"此前零散活跃日共 {trend_view['trimmed_active_days']} 个、{trend_view['trimmed_count']} 件，未纳入折线图。"
        )
    insights.append(_matchday_note(result, trend_view))
    return insights


def _insight_list(items: list[str], dark: bool = False) -> str:
    cls = "insights insights-dark" if dark else "insights"
    return f'<ul class="{cls}">{"".join(f"<li>{item}</li>" for item in items)}</ul>'


def _scope_strip(analysis: str, display: str, calc: str, dark: bool = False) -> str:
    mode = " scope-strip-dark" if dark else ""
    return f"""
    <div class="scope-strip{mode}" data-reveal="card">
      <div><span>分析要点</span><p>{_e(analysis)}</p></div>
      <div><span>展示方式</span><p>{_e(display)}</p></div>
      <div><span>计算说明</span><p>{_e(calc)}</p></div>
    </div>
    """


def _section_focus_title(section_focus: str) -> str:
    if section_focus == "distribution":
        return "问题分布概览"
    if section_focus == "trend":
        return "趋势与异动"
    return "整体情况"


def _section_focus_label(section_focus: str) -> str:
    if section_focus == "distribution":
        return "DISTRIBUTION"
    if section_focus == "trend":
        return "TREND & ANOMALY"
    return "OVERALL SITUATION"


def _section_focus_description(section_focus: str) -> str:
    if section_focus == "distribution":
        return "当前聚焦 1.1 问题分布概览，以 Elasticsearch 聚合结果呈现问题总量、类型分布、TOP 痛点与原因线索。"
    if section_focus == "trend":
        return "当前聚焦 1.2 投诉趋势与异动表现，以 Elasticsearch 聚合结果呈现按日波动、负向情绪占比与异常节点。"
    return "围绕模板定义的“问题分布概览”和“投诉趋势与异动表现”，以 Elasticsearch 聚合结果为核心，输出可审阅、可复盘、可直接用于汇报的 HTML 报告。"


def _analysis_type_text(section_focus: str) -> str:
    if section_focus == "distribution":
        return "1.1 问题分布概览"
    if section_focus == "trend":
        return "1.2 投诉趋势与异动表现"
    return "一、整体情况（1.1 + 1.2）"


def _top_secondary_label(result: dict) -> str:
    secondary = result.get("secondary", [])
    if not secondary:
        return "无"
    return str(secondary[0].get("key", "无"))


def _negative_peak_day(trend_view: dict[str, Any]) -> dict[str, Any] | None:
    days = trend_view.get("days", [])
    return max(days, key=lambda item: item["negative_ratio"], default=None)


def _hero_signal(section_focus: str, total: int, peak_day: dict[str, Any] | None, anomalies: list[dict]) -> tuple[str, str, str]:
    if section_focus == "trend":
        if peak_day:
            return "PEAK DAY", _e(peak_day["date"][5:]), f"峰值问题量 {_n(peak_day['count'])} 件"
        return "PEAK DAY", "无", "当前无可用趋势峰值"
    if section_focus == "distribution":
        return "TOTAL FEEDBACK", _n(total), "已纳入本次分布分析"
    return "LIVE SIGNAL", _n(total), "已纳入本周期反馈/投诉"


def _hero_issue(section_focus: str, top_primary: dict | None, top_tertiary: dict | None, anomalies: list[dict]) -> tuple[str, str, str]:
    if section_focus == "trend":
        if anomalies:
            first = anomalies[0]
            return "ANOMALY", _e(first["date"][5:]), f"首个明显异动日，日环比 {_pct(first.get('day_over_day_growth', 0))}"
        return "ANOMALY", "无", "当前未识别到明显异动日"
    if section_focus == "distribution":
        primary_name = _e(top_primary["key"]) if top_primary else "无"
        return "TOP CATEGORY", primary_name, "当前最集中的一级问题类型"
    top_issue = _e(top_tertiary["key"]) if top_tertiary else "无"
    return "TOP ISSUE", top_issue, "当前最需要优先定位的痛点"


def _build_kpis(section_focus: str, result: dict, total: int, top_primary: dict | None, top_tertiary: dict | None, peak_day: dict[str, Any] | None, trend_view: dict[str, Any]) -> list[dict[str, str]]:
    if section_focus == "distribution":
        return [
            {"label": "反馈/投诉总量", "value": _n(total)},
            {"label": "一级问题最高项", "value": _e(top_primary["key"]) if top_primary else "无"},
            {"label": "三级 TOP 问题", "value": _e(top_tertiary["key"]) if top_tertiary else "无"},
            {"label": "核心二级问题", "value": _e(_top_secondary_label(result))},
        ]
    if section_focus == "trend":
        return [
            {"label": "反馈/投诉总量", "value": _n(total)},
            {"label": "趋势峰值日", "value": _e(peak_day["date"][5:]) if peak_day else "无"},
            {"label": "峰值问题量", "value": _n(peak_day["count"]) if peak_day else "无"},
            {"label": "异动天数", "value": _n(len(trend_view.get("anomalies", [])))},
        ]
    return [
        {"label": "反馈/投诉总量", "value": _n(total)},
        {"label": "一级问题最高项", "value": _e(top_primary["key"]) if top_primary else "无"},
        {"label": "三级 TOP 问题", "value": _e(top_tertiary["key"]) if top_tertiary else "无"},
        {"label": "趋势峰值日", "value": _e(peak_day["date"][5:]) if peak_day else "无"},
    ]


def _query_note_text(query: dict, section_focus: str) -> str:
    note = str(query.get("note") or "").strip()
    if not note:
        return f"当前分析类型：{_analysis_type_text(section_focus)}。"
    cleaned = note.replace("section_focus为distribution", "当前聚焦 1.1 问题分布概览")
    cleaned = cleaned.replace("section_focus为trend", "当前聚焦 1.2 投诉趋势与异动表现")
    cleaned = cleaned.replace("section_focus为full", "当前聚焦完整“一、整体情况”")
    return cleaned


def render_html_report(result: dict, output_path: Path) -> Path:
    top_primary = result["primary"][0] if result.get("primary") else None
    top_secondary = result["secondary"][0] if result.get("secondary") else None
    top_tertiary = result["tertiary"][0] if result.get("tertiary") else None
    period_start = result["period"].get("min") or result["filters"].get("start_date") or "未限定"
    period_end = result["period"].get("max") or result["filters"].get("end_date") or "未限定"
    query = result.get("query") or {}
    section_focus = query.get("section_focus") or "full"
    trend_view = _build_trend_view(result.get("daily", []), result.get("filters", {}), result.get("anomalies", []))
    primary_total = _sum_counts(result.get("primary", []))
    secondary_total = _sum_counts(result.get("secondary", []))
    tertiary_total = _sum_counts(result.get("tertiary", []))
    peak_day = max(trend_view.get("days", []), key=lambda day: day["count"], default=None)
    total = result.get("total", 0)
    source_text = _source_files_text(result.get("source_files", []))
    schedule = _schedule_status(result)
    narratives = result.get("narratives") or {}
    trend_chart_summary = narratives.get("trend_chart_summary") or _trend_chart_summary(trend_view)
    trend_voice_items = _trend_voice_items(trend_view)
    trend_voice_summary = narratives.get("trend_voice_summary") or _trend_voice_summary(trend_voice_items)
    daily_focus_rows = _selected_daily_rows(trend_view.get("days", []), trend_view.get("anomalies", []))
    focus_title = _section_focus_title(section_focus)
    focus_label = _section_focus_label(section_focus)
    focus_description = _section_focus_description(section_focus)
    analysis_type = _analysis_type_text(section_focus)
    signal_label, signal_value, signal_desc = _hero_signal(section_focus, total, peak_day, trend_view.get("anomalies", []))
    issue_label, issue_value, issue_desc = _hero_issue(section_focus, top_primary, top_tertiary, trend_view.get("anomalies", []))
    kpis = _build_kpis(section_focus, result, total, top_primary, top_tertiary, peak_day, trend_view)

    question_line = f'<p class="subtle hero-meta">本次提问：{_e(query.get("question"))}</p>' if query.get("question") else ""
    analysis_line = f'<p class="subtle hero-meta">分析类型：{_e(analysis_type)}</p>'
    plan_note = f'<p class="subtle hero-meta">查询说明：{_e(_query_note_text(query, section_focus))}</p>'
    trend_window_line = (
        f'<p class="subtle hero-meta">趋势主分析时段：{_e(trend_view["start"])} 至 {_e(trend_view["end"])}</p>'
        if trend_view.get("used_focus_window") and section_focus in {"trend", "full"}
        else ""
    )
    query_section = (
        f"""
        <section class="chart-card chart-grid-wide" data-reveal="section" data-lazy="section">
          <div class="chart-header">
            <div>
              <span class="chart-kicker">QUERY CONTEXT</span>
              <h3>本次查询</h3>
            </div>
          </div>
          {question_line or '<p class="subtle hero-meta">本次提问：未提供</p>'}
          {plan_note}
        </section>
        """
        if query.get("question") or query.get("note")
        else ""
    )
    trend_window_note = (
        trend_view.get("note") or "当前按完整查询周期展示每日趋势。"
        if section_focus in {"trend", "full"}
        else "当前报告未展示 1.2 趋势章节。"
    )
    schedule_method_text = _matchday_note(result, trend_view)
    avg_duration = result.get("avg_duration_minutes")
    avg_duration_text = f"{float(avg_duration):.1f} 分钟" if isinstance(avg_duration, (int, float)) and not math.isnan(float(avg_duration)) else "未覆盖"
    primary_summary = (
        f"一级问题以「{top_primary['key']}」最集中，提及 {_n(top_primary['count'])} 次，占一级标签提及量的 {_pct(_safe_ratio(top_primary['count'], primary_total))}。"
        if top_primary
        else "当前没有可展示的一级问题数据。"
    )
    secondary_summary = (
        f"二级问题中「{top_secondary['key']}」提及 {_n(top_secondary['count'])} 次，占二级标签提及量的 {_pct(_safe_ratio(top_secondary['count'], secondary_total))}。"
        if top_secondary
        else "当前没有可展示的二级问题数据。"
    )
    tertiary_summary = (
        f"三级问题中「{top_tertiary['key']}」为核心痛点，提及 {_n(top_tertiary['count'])} 次，占三级标签提及量的 {_pct(_safe_ratio(top_tertiary['count'], tertiary_total))}。"
        if top_tertiary
        else "当前没有可展示的三级问题数据。"
    )

    distribution_section = f"""
    <section class="report-section" data-reveal="section" data-lazy="section">
      <div class="section-label"><span class="pulse-dot"></span><strong>SECTION 1.1</strong></div>
      <div class="section-heading">
        <div>
          <h2>1.1 问题分布概览</h2>
          <p>快速定位本周期最集中的用户痛点，判断哪一类问题需要优先投入资源解决。</p>
        </div>
      </div>
      {_scope_strip(
          "统计本周期相关问题的总量、一级/二级/三级标签分布、标签下钻关系和高频原因线索。",
          "图表（一级/二级/三级标签饼图、TOP5 三级问题柱状图）+ 标签下钻表 + 分析结论。",
          "通过 Elasticsearch 对 primary_labels、secondary_labels、tertiary_labels 做分层聚合，并按“一级→二级→三级”路径展开对应关系。",
      )}
      <div class="analysis-box analysis-box-gradient" data-reveal="card">
        <div class="analysis-header">
          <span class="chart-kicker">INSIGHT</span>
          <h3>分析结论</h3>
        </div>
        {_narrative_stack(narratives.get("distribution_conclusion") or _distribution_insights(result))}
      </div>
      <div class="grid chart-grid">
        {_donut_chart(result.get("primary", []), "一级标签类型分布", "一级标签提及量")}
        {_donut_chart(result.get("secondary", []), "二级标签类型分布", "二级标签提及量")}
        {_donut_chart(result.get("tertiary", []), "三级标签类型分布", "三级标签提及量")}
        {_top_bar_chart(result.get("tertiary", []))}
      </div>
      {_label_drilldown_table(result.get("primary_secondary_tertiary", []), primary_total)}
      <div class="section-stack chart-grid">
        {_overview_table("一级问题概览", "PRIMARY", result.get("primary", []), primary_total, narratives.get("primary_overview") or [primary_summary])}
        {_overview_table("二级问题概览", "SECONDARY", result.get("secondary", []), secondary_total, narratives.get("secondary_overview") or [secondary_summary])}
        {_overview_table("三级问题概览", "TERTIARY", result.get("tertiary", []), tertiary_total, narratives.get("tertiary_overview") or [tertiary_summary])}
      </div>
      <section class="chart-card chart-grid-wide" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">ISSUE CHAIN</span>
            <h3>问题链路归因</h3>
          </div>
        </div>
        {_narrative_stack(narratives.get("journey_summary"))}
        <div class="risk-stack">
          <div class="risk-row"><span>洞察维度</span><div class="chip-cloud">{_tags(result.get("insight_dimension", [])) or '<span class="subtle">暂无可展示数据。</span>'}</div></div>
          <div class="risk-row"><span>时段分布</span><div class="chip-cloud">{_tags(result.get("time_period", [])) or '<span class="subtle">暂无可展示数据。</span>'}</div></div>
          <div class="risk-row"><span>省份信息</span><div class="chip-cloud">{_tags(result.get("province", [])[:6]) or '<span class="subtle">暂无可展示数据。</span>'}</div></div>
          <div class="risk-row"><span>处理耗时</span><div class="chip-cloud"><span class="tag"><span class="tag-text">平均耗时</span><strong>{_e(avg_duration_text)}</strong></span></div></div>
        </div>
      </section>
      <section class="chart-card chart-grid-wide" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">OPERATION & LATENT NEED</span>
            <h3>运营举措与隐性诉求</h3>
          </div>
        </div>
        {_narrative_stack(narratives.get("operation_need_summary"))}
        {_operation_need_table(result.get("operation_need_examples", []))}
        {_latent_need_table(result.get("latent_need_examples", []))}
      </section>
      <section class="chart-card chart-grid-wide" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">MEMBER CLUSTER</span>
            <h3>会员类型聚类</h3>
          </div>
        </div>
        {_narrative_stack(narratives.get("member_cluster_summary"))}
        {_member_cluster_table(result.get("member_cluster_examples", []))}
      </section>
      <section class="chart-card chart-grid-wide" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">CAUSE CLUES</span>
            <h3>三级问题原因线索</h3>
          </div>
        </div>
        {_narrative_stack(narratives.get("cause_summary"))}
      </section>
      <section class="chart-card chart-grid-voice" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">USER VOICE</span>
            <h3>样例原声与原因研判</h3>
          </div>
        </div>
        {_narrative_stack(narratives.get("voice_summary"))}
        <div class="voice-grid">{_supporting_quotes(result.get("top_tertiary_examples", []))}</div>
      </section>
      <section class="chart-card chart-grid-voice" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">TYPICAL CASE</span>
            <h3>典型案例</h3>
          </div>
        </div>
        {_narrative_stack(narratives.get("case_summary"))}
        {_case_cards(result)}
      </section>
    </section>
    """

    trend_section = f"""
    <section class="report-section" data-reveal="section" data-lazy="section">
      <div class="section-label"><span class="pulse-dot"></span><strong>SECTION 1.2</strong></div>
      <div class="section-heading">
        <div>
          <h2>1.2 投诉趋势与异动表现</h2>
          <p>按日识别问题爆发的关键时间节点，结合赛事/事件线索解释异常波动的潜在原因。</p>
        </div>
      </div>
      {_scope_strip(
          "按日展示问题提及量和负向情绪指数的变化，标注赛事日。目的是识别问题爆发的关键时间节点，发现异常波动的潜在原因。",
          "图表（折线图 - 每日问题提及量及负向情绪指数）+ 图表分析总结 + 赛事日样例原声。",
          "通过 Elasticsearch 的 date_histogram 聚合统计各日期问题量趋势；活动日根据运行时传入的日历 Excel 按日期标注；当前无法严格计算负向情绪指数，使用负向情绪占比作为替代口径。",
      )}
      <div class="analysis-box analysis-box-gradient" data-reveal="card">
        <div class="analysis-header">
          <span class="chart-kicker">TREND INSIGHT</span>
          <h3>分析结论</h3>
        </div>
        {_narrative_stack(narratives.get("trend_conclusion") or _trend_insights(result, trend_view))}
      </div>
      {_trend_svg(trend_view.get("days", []), focus_note=trend_view.get("note"))}
      <section class="chart-card chart-grid-wide" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">CHART SUMMARY</span>
            <h3>图表分析总结</h3>
          </div>
        </div>
        {_narrative_stack(trend_chart_summary)}
      </section>
      <div class="grid chart-grid">
        <section class="chart-card" data-reveal="card">
          <div class="chart-header">
            <div>
              <span class="chart-kicker">EMOTION</span>
              <h3>情绪分布</h3>
            </div>
          </div>
          {_bar_rows(result.get("emotion", []))}
        </section>
        <section class="chart-card" data-reveal="card">
          <div class="chart-header">
            <div>
              <span class="chart-kicker">RISK</span>
              <h3>服务类型与升级风险</h3>
            </div>
          </div>
          <div class="risk-stack">
            <div class="risk-row"><span>服务类型</span><div class="chip-cloud">{_tags(result.get("service_type", []))}</div></div>
            <div class="risk-row"><span>退费诉求</span><div class="chip-cloud">{_tags(result.get("refund", []))}</div></div>
            <div class="risk-row"><span>升级投诉倾向</span><div class="chip-cloud">{_tags(result.get("escalation", []))}</div></div>
          </div>
        </section>
      </div>
      <section class="chart-card chart-grid-voice" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">TREND VOICE</span>
            <h3>样例原声与原因研判</h3>
          </div>
        </div>
        {_narrative_stack(trend_voice_summary)}
        {_trend_voice_cards(trend_voice_items)}
      </section>
      <section class="chart-card" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">DAILY DETAIL</span>
            <h3>日趋势明细（重点日期）</h3>
          </div>
        </div>
        <p class="subtle">为避免长日表淹没结论，本表默认展示峰值日、负向占比最高日、明显异动日及问题量靠前日期；完整趋势仍以折线图和聚合结果为准。</p>
        <div class="table-scroll">
          <table class="data-table daily-table">
            <thead>
              <tr><th>日期</th><th>问题量</th><th>日环比</th><th>负向情绪量</th><th>负向占比</th><th>赛事日标注</th><th>当日 TOP 三级问题</th></tr>
            </thead>
            <tbody>{_daily_rows(daily_focus_rows)}</tbody>
          </table>
        </div>
      </section>
      <section class="chart-card" data-reveal="card">
        <div class="chart-header">
          <div>
            <span class="chart-kicker">ANOMALY</span>
            <h3>异动节点</h3>
          </div>
        </div>
        {_narrative_stack(narratives.get("anomaly_summary"))}
        {_compact_anomaly_cards(trend_view.get("anomalies", []))}
      </section>
    </section>
    """

    if section_focus == "distribution":
        selected_sections = distribution_section
    elif section_focus == "trend":
        selected_sections = trend_section
    else:
        selected_sections = distribution_section + trend_section

    summary_section = _executive_summary_section(result, narratives, trend_view)

    style = """
  <style>
    :root {
      --background: #FAFAFA;
      --foreground: #0F172A;
      --muted: #F1F5F9;
      --muted-foreground: #64748B;
      --accent: #0052FF;
      --accent-secondary: #4D7CFF;
      --accent-strong: #1D4FFF;
      --accent-soft: rgba(0,82,255,0.08);
      --border: #E2E8F0;
      --card: #FFFFFF;
      --shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
      --shadow-hover: 0 18px 42px rgba(15, 23, 42, 0.14);
      --radius: 8px;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body, h1, h2, h3, h4, p, div, span, td, th, strong {
      writing-mode: horizontal-tb;
      text-orientation: mixed;
    }
    body {
      margin: 0;
      font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
      color: var(--foreground);
      background:
        radial-gradient(circle at top right, rgba(77,124,255,0.14), transparent 26%),
        radial-gradient(circle at top left, rgba(0,82,255,0.08), transparent 24%),
        var(--background);
      line-height: 1.65;
    }
    .page {
      max-width: 1160px;
      margin: 0 auto;
      padding: 36px 22px 72px;
    }
    .has-js [data-reveal] {
      opacity: 0;
      transform: translate3d(0, 30px, 0) scale(0.985);
      filter: blur(10px);
      transition:
        opacity .72s cubic-bezier(.16,1,.3,1),
        transform .72s cubic-bezier(.16,1,.3,1),
        filter .72s cubic-bezier(.16,1,.3,1);
      transition-delay: calc(var(--reveal-order, 0) * 55ms);
      will-change: opacity, transform, filter;
    }
    .has-js [data-reveal="section"] {
      transform: translate3d(0, 38px, 0);
      transition-duration: .82s;
    }
    .has-js [data-reveal="item"] {
      transform: translate3d(0, 22px, 0) scale(0.992);
      transition-duration: .62s;
    }
    .has-js [data-reveal].is-visible {
      opacity: 1;
      transform: translate3d(0, 0, 0) scale(1);
      filter: none;
    }
    [data-lazy="section"] {
      contain: layout paint style;
    }
    @supports (content-visibility: auto) {
      [data-lazy="section"] {
        content-visibility: auto;
        contain-intrinsic-size: 920px;
      }
      .section-dark[data-lazy="section"] {
        contain-intrinsic-size: 1180px;
      }
    }
    .hero {
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 28px;
      align-items: stretch;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 34px;
      overflow: hidden;
      position: relative;
      animation: fade-up .8s cubic-bezier(.16,1,.3,1) both;
    }
    .hero::before {
      content: "";
      position: absolute;
      inset: auto auto -120px -120px;
      width: 280px;
      height: 280px;
      background: radial-gradient(circle, rgba(0,82,255,0.12), transparent 70%);
      filter: blur(4px);
      pointer-events: none;
    }
    .hero::after {
      content: "";
      position: absolute;
      inset: auto 0 0 0;
      height: 4px;
      background: linear-gradient(90deg, var(--accent), var(--accent-secondary));
    }
    .hero-copy { position: relative; z-index: 1; }
    .section-label {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 14px;
      border-radius: 999px;
      border: 1px solid rgba(0,82,255,0.26);
      background: rgba(0,82,255,0.06);
      color: var(--accent);
      font-family: "JetBrains Mono", Consolas, monospace;
      font-size: 12px;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .section-label-light {
      border-color: rgba(255,255,255,0.18);
      background: rgba(255,255,255,0.08);
      color: rgba(255,255,255,0.9);
    }
    .pulse-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
      box-shadow: 0 0 0 0 rgba(77,124,255,0.35);
      animation: pulse 2.4s ease-in-out infinite;
    }
    h1, h2 {
      font-family: "Calistoga", Georgia, "Times New Roman", "Microsoft YaHei", serif;
      margin: 0;
      font-weight: 400;
    }
    h1 {
      font-size: clamp(2.9rem, 6vw, 5.05rem);
      line-height: 1.05;
      margin-top: 18px;
      max-width: 9ch;
      position: relative;
    }
    h2 {
      font-size: clamp(2rem, 4vw, 3.25rem);
      line-height: 1.12;
    }
    h3 {
      margin: 0;
      font-size: 1.25rem;
      line-height: 1.3;
      font-weight: 600;
    }
    h4 {
      margin: 0;
      font-size: 1.05rem;
      line-height: 1.35;
      font-weight: 600;
    }
    .gradient-text {
      background: linear-gradient(90deg, var(--accent), var(--accent-secondary));
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
    .hero-copy .lead {
      margin: 18px 0 0;
      max-width: 700px;
      color: var(--muted-foreground);
      font-size: 1.05rem;
    }
    .subtle { color: var(--muted-foreground); }
    .hero-meta {
      margin: 12px 0 0;
      font-size: 0.95rem;
      max-width: 100%;
      word-break: break-word;
      overflow-wrap: anywhere;
    }
    .hero-visual {
      position: relative;
      min-height: 320px;
      border-radius: var(--radius);
      overflow: hidden;
      background:
        radial-gradient(circle, rgba(255,255,255,0.035) 1px, transparent 1px) 0 0 / 26px 26px,
        #0F172A;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06);
      animation: fade-up .85s cubic-bezier(.16,1,.3,1) both .08s;
    }
    .hero-glow {
      position: absolute;
      inset: auto -10% -18% auto;
      width: 260px;
      height: 260px;
      background: radial-gradient(circle, rgba(77,124,255,0.34), transparent 70%);
      filter: blur(28px);
    }
    .hero-ring {
      position: absolute;
      width: 280px;
      height: 280px;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      border-radius: 50%;
      border: 1px dashed rgba(255,255,255,0.24);
      animation: spin 60s linear infinite;
    }
    .hero-orbit {
      position: absolute;
      width: 220px;
      height: 220px;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      border-radius: 50%;
      border: 1px solid rgba(255,255,255,0.08);
    }
    .hero-block {
      position: absolute;
      border-radius: 8px;
      background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
      box-shadow: 0 10px 28px rgba(0,82,255,0.34);
    }
    .hero-block-a { width: 72px; height: 72px; top: 26px; right: 28px; }
    .hero-block-b { width: 22px; height: 22px; bottom: 26px; left: 28px; }
    .float-card {
      position: absolute;
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.12);
      backdrop-filter: blur(12px);
      border-radius: 8px;
      padding: 14px 16px;
      color: #FFFFFF;
      min-width: 170px;
      box-shadow: 0 16px 34px rgba(15,23,42,0.26);
    }
    .float-card strong { display: block; font-size: 1.75rem; line-height: 1; margin-top: 6px; }
    .float-card small { color: rgba(255,255,255,0.72); font-size: 0.8rem; }
    .float-card-1 { top: 38px; left: 30px; animation: float-a 5.2s ease-in-out infinite; }
    .float-card-2 { bottom: 40px; right: 34px; animation: float-b 4.6s ease-in-out infinite; }
    .hero-badge {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.16);
      background: rgba(255,255,255,0.08);
      font-size: 0.82rem;
    }
    .hero-badge .pulse-dot { transform: scale(.9); }
    .kpis {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      margin: 28px 0 0;
    }
    .kpi {
      position: relative;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px 18px 20px;
      box-shadow: var(--shadow);
      min-height: 132px;
      overflow: hidden;
      transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
      animation: fade-up .8s cubic-bezier(.16,1,.3,1) both;
    }
    .kpi:nth-child(1){ animation-delay:.10s; }
    .kpi:nth-child(2){ animation-delay:.16s; }
    .kpi:nth-child(3){ animation-delay:.22s; }
    .kpi:nth-child(4){ animation-delay:.28s; }
    .kpi::after {
      content: "";
      position: absolute;
      inset: auto -18% -52% auto;
      width: 160px;
      height: 160px;
      background: radial-gradient(circle, rgba(0,82,255,0.12), transparent 68%);
    }
    .kpi:hover {
      transform: translateY(-4px);
      box-shadow: var(--shadow-hover);
      border-color: rgba(0,82,255,0.28);
    }
    .kpi .label {
      color: var(--muted-foreground);
      font-size: 0.82rem;
      margin-bottom: 10px;
    }
    .kpi .value {
      font-size: clamp(1.7rem, 3vw, 2.55rem);
      font-weight: 800;
      line-height: 1.1;
      word-break: break-word;
      overflow-wrap: anywhere;
    }
    .report-section {
      margin-top: 48px;
    }
    .section-dark {
      margin-top: 56px;
      padding: 34px;
      border-radius: var(--radius);
      background:
        radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px) 0 0 / 28px 28px,
        radial-gradient(circle at top right, rgba(77,124,255,0.18), transparent 22%),
        #0F172A;
      position: relative;
      overflow: hidden;
      box-shadow: 0 22px 44px rgba(15,23,42,0.22);
    }
    .section-dark::before {
      content: "";
      position: absolute;
      inset: -10% auto auto -12%;
      width: 280px;
      height: 280px;
      background: radial-gradient(circle, rgba(77,124,255,0.22), transparent 70%);
      filter: blur(18px);
      pointer-events: none;
    }
    .section-heading {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: end;
      margin: 16px 0 18px;
    }
    .section-heading p {
      margin: 10px 0 0;
      max-width: 760px;
      color: var(--muted-foreground);
      font-size: 1rem;
    }
    .section-heading-dark p { color: rgba(255,255,255,0.74); }
    .light-title { color: #FFFFFF; }
    .scope-strip {
      display: grid;
      grid-template-columns: 1.2fr 0.95fr 1.2fr;
      gap: 1px;
      background: var(--border);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .scope-strip > div {
      background: var(--card);
      padding: 16px;
    }
    .scope-strip span {
      display: inline-block;
      color: var(--accent);
      font-weight: 700;
      font-size: 0.8rem;
      margin-bottom: 6px;
    }
    .scope-strip p {
      margin: 0;
      color: var(--muted-foreground);
      font-size: 0.92rem;
    }
    .scope-strip-dark {
      background: rgba(255,255,255,0.08);
      border-color: rgba(255,255,255,0.1);
    }
    .scope-strip-dark > div { background: rgba(255,255,255,0.04); }
    .scope-strip-dark span { color: #8FB0FF; }
    .scope-strip-dark p { color: rgba(255,255,255,0.72); }
    .analysis-box {
      margin-top: 18px;
      padding: 20px 22px;
      border-radius: var(--radius);
      border: 1px solid var(--border);
      background: var(--card);
      box-shadow: var(--shadow);
      transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
    }
    .analysis-box:hover {
      transform: translateY(-4px);
      box-shadow: var(--shadow-hover);
      border-color: rgba(0,82,255,0.22);
    }
    .analysis-box-gradient {
      background: linear-gradient(135deg, rgba(0,82,255,0.08), rgba(255,255,255,0.96));
      border-color: rgba(0,82,255,0.18);
    }
    .analysis-box-dark {
      background: rgba(255,255,255,0.05);
      border-color: rgba(255,255,255,0.12);
      box-shadow: none;
    }
    .analysis-header {
      display: flex;
      align-items: baseline;
      gap: 14px;
      margin-bottom: 10px;
    }
    .module-summary {
      margin: 0 0 14px;
      color: var(--muted-foreground);
      font-size: 0.96rem;
    }
    .narrative-stack {
      display: grid;
      gap: 10px;
      margin: 0 0 14px;
    }
    .narrative-stack p {
      margin: 0;
      color: var(--muted-foreground);
      font-size: 0.97rem;
      line-height: 1.72;
    }
    .narrative-stack-dark p {
      color: rgba(255,255,255,0.86);
    }
    .metric-pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: flex-start;
    }
    .metric-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
      padding: 6px 12px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: rgba(0,82,255,0.04);
      color: var(--foreground);
      line-height: 1.4;
    }
    .metric-pill strong {
      font-size: 0.88rem;
      font-weight: 700;
    }
    .metric-pill span {
      color: var(--accent);
      font-size: 0.84rem;
      font-weight: 700;
      white-space: nowrap;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      align-items: start;
    }
    .section-stack {
      display: grid;
      gap: 18px;
    }
    .chart-grid { margin-top: 18px; }
    .chart-grid-wide { margin-top: 18px; }
    .chart-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 20px;
      box-shadow: var(--shadow);
      transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
    }
    .chart-card:hover {
      transform: translateY(-4px);
      box-shadow: var(--shadow-hover);
      border-color: rgba(0,82,255,0.22);
    }
    .chart-card-highlight {
      background: linear-gradient(135deg, rgba(0,82,255,0.06), rgba(255,255,255,1));
      border-color: rgba(0,82,255,0.18);
    }
    .chart-card-dark {
      margin-top: 18px;
      background: transparent;
      border-color: rgba(255,255,255,0.1);
      box-shadow: none;
      color: #FFFFFF;
      padding: 20px 0 0;
    }
    .chart-card-dark:hover {
      transform: none;
      box-shadow: none;
      border-color: rgba(255,255,255,0.1);
    }
    .chart-card-light { margin-top: 18px; }
    .chart-header {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 14px;
    }
    .chart-header-dark { padding: 0 0 8px; }
    .chart-kicker {
      display: inline-block;
      color: var(--accent);
      font-family: "JetBrains Mono", Consolas, monospace;
      font-size: 0.78rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    .chart-kicker-light { color: #9EB6FF; }
    .pie-layout {
      display: grid;
      grid-template-columns: 248px 1fr;
      gap: 16px;
      align-items: center;
    }
    .donut-chart {
      width: 232px;
      height: 232px;
      display: block;
      margin: 0 auto;
    }
    .donut-total {
      font-size: 1.95rem;
      font-weight: 800;
      fill: var(--foreground);
    }
    .donut-caption {
      font-size: 0.74rem;
      fill: var(--muted-foreground);
    }
    .legend-stack {
      display: grid;
      gap: 10px;
      min-width: 0;
    }
    .legend-row {
      display: grid;
      grid-template-columns: 12px minmax(0, 1fr) auto auto;
      gap: 10px;
      align-items: center;
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: rgba(255,255,255,0.84);
    }
    .legend-swatch {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    .legend-name {
      min-width: 0;
      word-break: normal;
      overflow-wrap: anywhere;
    }
    .legend-share { color: var(--muted-foreground); }
    .rank-chart {
      display: grid;
      gap: 14px;
      margin-top: 6px;
    }
    .rank-row {
      display: grid;
      grid-template-columns: 48px minmax(150px, 220px) 1fr 54px;
      gap: 12px;
      align-items: center;
    }
    .rank-index {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, rgba(0,82,255,0.12), rgba(77,124,255,0.22));
      color: var(--accent-strong);
      font-weight: 700;
      font-family: "JetBrains Mono", Consolas, monospace;
    }
    .rank-label {
      min-width: 0;
      font-weight: 600;
      word-break: keep-all;
      overflow-wrap: break-word;
    }
    .rank-track {
      height: 16px;
      background: var(--muted);
      border-radius: 999px;
      overflow: hidden;
      position: relative;
    }
    .rank-fill {
      width: var(--target-width);
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--accent), var(--accent-secondary));
      transform-origin: left center;
      transform: scaleX(0);
    }
    .rank-value {
      text-align: right;
      font-weight: 700;
      color: var(--muted-foreground);
      white-space: nowrap;
    }
    .bar-row {
      display: grid;
      grid-template-columns: minmax(110px, 140px) 1fr 42px;
      gap: 12px;
      align-items: center;
      margin: 10px 0;
    }
    .bar-label {
      min-width: 0;
      word-break: keep-all;
      overflow-wrap: break-word;
    }
    .bar-track {
      height: 16px;
      background: var(--muted);
      border-radius: 999px;
      overflow: hidden;
      position: relative;
    }
    .bar-fill {
      width: var(--target-width);
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--accent), var(--accent-secondary));
      transform-origin: left center;
      transform: scaleX(0);
    }
    .bar-fill.alt {
      background: linear-gradient(90deg, #F97316, #FDBA74);
    }
    .bar-value {
      text-align: right;
      font-weight: 700;
      color: var(--muted-foreground);
      white-space: nowrap;
    }
    .risk-stack {
      display: grid;
      gap: 12px;
    }
    .risk-row {
      display: grid;
      grid-template-columns: 96px 1fr;
      gap: 12px;
      align-items: start;
      padding: 12px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: rgba(255,255,255,0.85);
    }
    .risk-row > span {
      font-size: 0.9rem;
      font-weight: 700;
      color: var(--muted-foreground);
      padding-top: 4px;
    }
    .detail-grid, .voice-grid, .signal-grid {
      display: grid;
      gap: 14px;
    }
    .detail-card, .voice-card, .signal-card {
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: linear-gradient(135deg, rgba(0,82,255,0.03), rgba(255,255,255,0.98));
      padding: 16px;
      transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
    }
    .detail-card:hover, .voice-card:hover, .signal-card:hover {
      transform: translateY(-4px);
      box-shadow: var(--shadow);
      border-color: rgba(0,82,255,0.22);
    }
    .detail-head, .voice-head, .signal-card-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      margin-bottom: 12px;
    }
    .detail-head p, .signal-card p, .voice-meta {
      margin: 6px 0 0;
      color: var(--muted-foreground);
      font-size: 0.92rem;
    }
    .detail-count, .voice-head span {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 44px;
      height: 32px;
      padding: 0 10px;
      border-radius: 999px;
      background: rgba(0,82,255,0.08);
      color: var(--accent);
      font-weight: 700;
      white-space: nowrap;
    }
    .voice-body { display: grid; gap: 8px; }
    .quote {
      position: relative;
      padding: 12px 14px 12px 16px;
      border-radius: var(--radius);
      border-left: 3px solid var(--accent);
      background: rgba(0,82,255,0.04);
      color: var(--muted-foreground);
      word-break: break-word;
      overflow-wrap: anywhere;
    }
    .chip-cloud {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: flex-start;
    }
    .tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 34px;
      max-width: 100%;
      padding: 6px 10px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.94);
      white-space: normal;
      word-break: break-word;
      overflow-wrap: anywhere;
      line-height: 1.45;
      box-shadow: 0 1px 2px rgba(15,23,42,0.04);
    }
    .tag strong {
      white-space: nowrap;
      color: var(--foreground);
    }
    .tag-text {
      min-width: 0;
      overflow-wrap: anywhere;
    }
    .insights {
      margin: 0;
      padding-left: 20px;
    }
    .insights li { margin: 8px 0; }
    .insights-dark li { color: rgba(255,255,255,0.88); }
    .trend-svg {
      width: 100%;
      height: auto;
      display: block;
      border-radius: var(--radius);
      margin-top: 6px;
    }
    .axis-tick {
      font-size: 12px;
      fill: var(--muted-foreground);
    }
    .axis-tick-dark {
      fill: rgba(255,255,255,0.68);
    }
    .axis-title {
      font-size: 13px;
      font-weight: 700;
    }
    .axis-title-dark {
      fill: rgba(255,255,255,0.92);
    }
    .event-label {
      font-size: 11px;
      font-weight: 700;
      fill: #9EB6FF;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      margin-top: 14px;
      color: var(--muted-foreground);
      font-size: 0.92rem;
    }
    .legend-light { color: rgba(255,255,255,0.82); }
    .trend-note {
      margin: 12px 0 2px;
      color: var(--muted-foreground);
      font-size: 0.9rem;
      line-height: 1.6;
    }
    .event-summary {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    .event-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 32px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(0,82,255,0.14);
      background: rgba(0,82,255,0.05);
      color: var(--muted-foreground);
      font-size: 0.84rem;
      line-height: 1.4;
    }
    .event-pill-strong {
      background: rgba(0,82,255,0.08);
      border-color: rgba(0,82,255,0.24);
    }
    .event-pill-peak {
      box-shadow: 0 0 0 1px rgba(0,82,255,0.16) inset;
    }
    .event-pill strong {
      color: var(--accent);
      white-space: nowrap;
    }
    .dot {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 6px;
      vertical-align: middle;
    }
    .dot.count { background: linear-gradient(135deg, #0052FF, #4D7CFF); }
    .dot.negative { background: linear-gradient(135deg, #F97316, #FDBA74); }
    .dot.event { background: #9EB6FF; }
    .table-scroll {
      overflow-x: auto;
      padding-bottom: 4px;
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      min-width: 920px;
      font-size: 0.92rem;
    }
    .drilldown-table {
      min-width: 1280px;
    }
    .data-table th,
    .data-table td {
      padding: 12px 12px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
      line-height: 1.55;
      white-space: normal;
      word-break: keep-all;
      overflow-wrap: break-word;
    }
    .data-table th {
      font-size: 0.78rem;
      color: var(--muted-foreground);
      background: var(--muted);
      font-weight: 700;
    }
    .data-table tr:last-child td { border-bottom: 0; }
    .analysis-box strong { display: inline-block; margin-bottom: 6px; }
    .signal-chip {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      height: 30px;
      padding: 0 10px;
      border-radius: 999px;
      background: rgba(0,82,255,0.1);
      color: var(--accent);
      font-size: 0.82rem;
      font-weight: 700;
      white-space: nowrap;
    }
    .signal-meta {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 12px;
    }
    .signal-meta span {
      display: inline-block;
      color: var(--muted-foreground);
      font-size: 0.76rem;
      margin-bottom: 4px;
      font-weight: 700;
    }
    .signal-meta p {
      margin: 0;
      font-size: 0.9rem;
      word-break: break-word;
      overflow-wrap: anywhere;
    }
    .signal-note {
      margin: 12px 0 0 !important;
      color: var(--muted-foreground);
      font-size: 0.84rem !important;
      line-height: 1.55;
    }
    .day-marker {
      display: grid;
      gap: 8px;
      min-width: 220px;
    }
    .day-marker-copy {
      display: grid;
      gap: 6px;
      min-width: 0;
    }
    .day-marker-copy strong {
      color: var(--foreground);
      font-size: 0.92rem;
      line-height: 1.45;
      word-break: break-word;
      overflow-wrap: anywhere;
    }
    .day-marker-subtle {
      color: var(--muted-foreground);
      font-size: 0.82rem;
      line-height: 1.5;
    }
    .match-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 28px;
      width: fit-content;
      padding: 0 10px;
      border-radius: 999px;
      background: rgba(0,82,255,0.1);
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 700;
      white-space: nowrap;
    }
    .match-pill-muted {
      background: var(--muted);
      color: var(--muted-foreground);
    }
    .match-pill-dark {
      background: rgba(158,182,255,0.16);
      color: #C8D7FF;
    }
    .match-pill-muted-dark {
      background: rgba(255,255,255,0.08);
      color: rgba(255,255,255,0.76);
    }
    .footnote {
      margin-top: 46px;
    }
    .has-js [data-reveal].is-visible .rank-fill {
      animation: grow-x 1.05s cubic-bezier(.16,1,.3,1) both;
    }
    .has-js [data-reveal].is-visible .bar-fill {
      animation: grow-x 1s cubic-bezier(.16,1,.3,1) both;
    }
    html:not(.has-js) .rank-fill {
      animation: grow-x 1.05s cubic-bezier(.16,1,.3,1) both;
    }
    html:not(.has-js) .bar-fill {
      animation: grow-x 1s cubic-bezier(.16,1,.3,1) both;
    }
    @keyframes spin {
      from { transform: translate(-50%, -50%) rotate(0deg); }
      to { transform: translate(-50%, -50%) rotate(360deg); }
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(77,124,255,0.38); }
      50% { transform: scale(1.24); box-shadow: 0 0 0 8px rgba(77,124,255,0); }
    }
    @keyframes float-a {
      0%, 100% { transform: translateY(0px); }
      50% { transform: translateY(-10px); }
    }
    @keyframes float-b {
      0%, 100% { transform: translateY(0px); }
      50% { transform: translateY(10px); }
    }
    @keyframes grow-x {
      from { transform: scaleX(0); }
      to { transform: scaleX(1); }
    }
    @keyframes fade-up {
      from { opacity: 0; transform: translateY(26px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
      .has-js [data-reveal] {
        opacity: 1 !important;
        transform: none !important;
        filter: none !important;
      }
    }
    @media (max-width: 1100px) {
      .hero,
      .kpis,
      .grid,
      .pie-layout,
      .scope-strip,
      .signal-meta {
        grid-template-columns: 1fr;
      }
      .hero { padding: 28px; }
      .hero-visual { min-height: 280px; }
      .rank-row {
        grid-template-columns: 40px minmax(130px, 1fr) 1fr 48px;
      }
      .risk-row { grid-template-columns: 88px 1fr; }
    }
    @media (max-width: 760px) {
      .page { padding: 22px 14px 52px; }
      .hero,
      .section-dark {
        padding: 22px 18px;
      }
      .kpis { gap: 12px; }
      .kpi { min-height: 112px; }
      .section-heading { display: block; }
      .section-heading p { margin-top: 10px; }
      .chart-card, .analysis-box { padding: 16px; }
      .bar-row {
        grid-template-columns: minmax(88px, 110px) 1fr 34px;
        gap: 8px;
      }
      .rank-row {
        grid-template-columns: 34px minmax(104px, 1fr);
        gap: 10px;
      }
      .rank-track, .rank-value { grid-column: 2; }
      .rank-value { text-align: left; }
      .risk-row { grid-template-columns: 1fr; }
      .tag { width: 100%; justify-content: space-between; }
      .data-table { min-width: 760px; }
    }
  </style>
    """

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
   <title>一、整体情况 - 视频业务用户反馈分析</title>
  <script>document.documentElement.classList.add("has-js");</script>
  {style}
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="hero-copy">
        <div class="section-label"><span class="pulse-dot"></span><strong>{_e(focus_label)}</strong></div>
         <h1>视频业务用户反馈<span class="gradient-text">{_e(focus_title)}</span></h1>
        <p class="lead">{_e(focus_description)}</p>
        <p class="subtle hero-meta">报告周期：{_e(period_start)} 至 {_e(period_end)}</p>
        {analysis_line}
        {trend_window_line}
      </div>
      <div class="hero-visual">
        <div class="hero-glow"></div>
        <div class="hero-ring"></div>
        <div class="hero-orbit"></div>
        <div class="hero-block hero-block-a"></div>
        <div class="hero-block hero-block-b"></div>
        <div class="float-card float-card-1">
          <div class="hero-badge"><span class="pulse-dot"></span><span>{_e(signal_label)}</span></div>
          <strong>{_e(signal_value)}</strong>
          <small>{_e(signal_desc)}</small>
        </div>
        <div class="float-card float-card-2">
          <div class="hero-badge"><span class="pulse-dot"></span><span>{_e(issue_label)}</span></div>
          <strong>{_e(issue_value)}</strong>
          <small>{_e(issue_desc)}</small>
        </div>
      </div>
    </section>

    {summary_section}

    {query_section}

    <section class="kpis">
      {"".join(f'<article class="kpi"><div class="label">{_e(item["label"])}</div><div class="value">{_e(item["value"])}</div></article>' for item in kpis)}
    </section>

    {selected_sections}

    <section class="chart-card footnote" data-reveal="section" data-lazy="section">
      <div class="chart-header">
        <div>
          <span class="chart-kicker">METHOD</span>
          <h3>口径说明</h3>
        </div>
      </div>
      <div class="table-scroll">
        <table class="data-table">
          <tbody>
            <tr><th>数据来源</th><td>{_e(source_text)} 已导入 Elasticsearch，并通过聚合查询生成。</td></tr>
            <tr><th>适用范围</th><td>{_e(analysis_type)}。</td></tr>
            <tr><th>负向情绪</th><td>当前以「愤怒、失望、焦虑、不满、烦躁」作为负向情绪集合。</td></tr>
            <tr><th>赛事日标注</th><td>{_e(schedule_method_text)}</td></tr>
            <tr><th>趋势窗口</th><td>{_e(trend_window_note)}</td></tr>
            <tr><th>多标签统计</th><td>一级、二级、三级及业务等多值字段按分隔符拆分后聚合，因此同一工单可贡献到多个标签桶。</td></tr>
            <tr><th>用户属性字段</th><td>当前新增表头包含省份、服务时间、时段、处理耗时、会员类型聚类等基础信息；未包含终端型号、App 版本字段，报告不做该维度推断。</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
  <script>
    (() => {{
      const prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const revealNodes = Array.from(document.querySelectorAll("[data-reveal]"));
      if (!revealNodes.length) {{
        return;
      }}
      const sectionRoots = revealNodes.filter((node) => node.dataset.reveal === "section");
      const observedNodes = sectionRoots.length
        ? sectionRoots
        : revealNodes.filter((node) => !node.closest('[data-reveal="section"]') || node.dataset.reveal === "section");
      const pending = new Set(observedNodes);

      const show = (node, immediate) => {{
        if (node.classList.contains("is-visible")) {{
          return;
        }}
        if (immediate) {{
          node.style.transitionDelay = "0ms";
        }}
        node.classList.add("is-visible");
      }};

      const revealBranch = (root, immediate) => {{
        show(root, immediate);
        const children = Array.from(root.querySelectorAll("[data-reveal]")).filter((node) => node !== root);
        children.forEach((node, index) => {{
          node.style.setProperty("--reveal-order", String(Math.min(index + 1, 8)));
          const activate = () => show(node, immediate);
          if (immediate) {{
            activate();
            return;
          }}
          window.setTimeout(activate, Math.min(index, 8) * 55);
        }});
      }};

      const isNearViewport = (node) => {{
        const rect = node.getBoundingClientRect();
        const enterTop = window.innerHeight * 0.96;
        const leaveBottom = -160;
        return rect.top <= enterTop && rect.bottom >= leaveBottom;
      }};

      const activateNode = (node, immediate) => {{
        if (!pending.has(node)) {{
          return;
        }}
        pending.delete(node);
        if (node.dataset.reveal === "section") {{
          revealBranch(node, immediate);
          return;
        }}
        show(node, immediate);
      }};

      const checkPending = () => {{
        pending.forEach((node) => {{
          if (isNearViewport(node)) {{
            activateNode(node, false);
          }}
        }});
        if (!pending.size) {{
          window.removeEventListener("scroll", checkPending, passiveOptions);
          window.removeEventListener("resize", checkPending);
        }}
      }};

      const passiveOptions = {{ passive: true }};

      if (prefersReducedMotion || !("IntersectionObserver" in window)) {{
        observedNodes.forEach((node) => {{
          activateNode(node, true);
        }});
        return;
      }}

      const observer = new IntersectionObserver(
        (entries) => {{
          entries.forEach((entry) => {{
            if (!entry.isIntersecting && !isNearViewport(entry.target)) {{
              return;
            }}
            activateNode(entry.target, false);
            observer.unobserve(entry.target);
          }});
        }},
        {{
          threshold: 0,
          rootMargin: "160px 0px -12% 0px",
        }},
      );

      observedNodes.forEach((node, index) => {{
        node.style.setProperty("--reveal-order", String(index % 4));
        if (isNearViewport(node)) {{
          activateNode(node, true);
        }} else {{
          observer.observe(node);
        }}
      }});

      if (pending.size) {{
        window.addEventListener("scroll", checkPending, passiveOptions);
        window.addEventListener("resize", checkPending);
        window.requestAnimationFrame(checkPending);
      }}
    }})();
  </script>
</body>
</html>
"""

    html = enforce_style_contract(html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
