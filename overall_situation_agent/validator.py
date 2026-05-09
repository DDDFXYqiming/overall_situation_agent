from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .template_contract import OVERALL_SITUATION_SECTIONS


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]


def validate_user_question(question: str) -> ValidationResult:
    cleaned = question.strip()
    errors = []
    if not cleaned:
        errors.append("问题不能为空。")
    if len(cleaned) < 4:
        errors.append("问题过短，请至少说明要分析整体情况或报告周期。")
    if len(cleaned) > 300:
        errors.append("问题过长，请控制在 300 字以内。")
    if re.search(r"<script|</html|<iframe", cleaned, flags=re.IGNORECASE):
        errors.append("问题中包含不允许的 HTML/脚本片段。")
    return ValidationResult(ok=not errors, errors=errors)


def validate_report_result(result: dict) -> ValidationResult:
    errors = []
    for key in ["total", "primary", "secondary", "tertiary", "daily", "primary_secondary", "primary_secondary_tertiary", "top_tertiary_examples"]:
        if key not in result:
            errors.append(f"聚合结果缺少字段：{key}")
    if "period" not in result or "filters" not in result:
        errors.append("聚合结果缺少周期信息。")
    return ValidationResult(ok=not errors, errors=errors)


def validate_html_report(path: Path) -> ValidationResult:
    if not path.exists():
        return ValidationResult(False, [f"报告文件不存在：{path}"])
    html = path.read_text(encoding="utf-8")
    lower = html.lower()
    errors = [f"HTML 缺少必要分析维度：{dim}" for dim in OVERALL_SITUATION_SECTIONS if dim not in html]
    if "<script" in lower and "<script src" in lower:
        errors.append("HTML 中不允许引用外部 script 资源。")
    if "http://" in lower or "https://" in lower:
        errors.append("HTML 中不允许引用外部网络资源。")
    return ValidationResult(ok=not errors, errors=errors)


def validate_html_report_for_focus(path: Path, section_focus: str = "full") -> ValidationResult:
    if not path.exists():
        return ValidationResult(False, [f"报告文件不存在：{path}"])
    html = path.read_text(encoding="utf-8")
    lower = html.lower()
    if section_focus == "distribution":
        required = [
            "1.1 问题分布概览",
            "一级标签类型分布",
            "二级标签类型分布",
            "三级标签类型分布",
            "TOP5 三级问题提及量",
            "一级问题概览",
            "二级问题概览",
            "三级问题概览",
            "三级问题原因线索、样例原声与典型案例",
        ]
    elif section_focus == "trend":
        required = [
            "1.2 投诉趋势与异动表现",
            "每日问题提及量与负向情绪占比",
            "图表分析总结",
            "赛事日用户原声",
            "异动节点",
        ]
    else:
        required = OVERALL_SITUATION_SECTIONS
    errors = [f"HTML 缺少必要分析维度：{dim}" for dim in required if dim not in html]
    if "<script" in lower and "<script src" in lower:
        errors.append("HTML 中不允许引用外部 script 资源。")
    if "http://" in lower or "https://" in lower:
        errors.append("HTML 中不允许引用外部网络资源。")
    return ValidationResult(ok=not errors, errors=errors)
