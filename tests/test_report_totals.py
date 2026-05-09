from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from overall_situation_agent.markdown_renderer import render_markdown_report
from overall_situation_agent.report import _compact_anomaly_cards, _distribution_insights, _trend_insights, render_html_report
from overall_situation_agent.validator import validate_html_report_for_focus


def _result() -> dict:
    return {
        "total": 10,
        "total_with_unlabeled": 14,
        "period": {"min": "2026-03-01", "max": "2026-03-31"},
        "filters": {},
        "query": {"section_focus": "distribution"},
        "primary": [{"key": "业务体验", "count": 10}],
        "secondary": [{"key": "权益使用", "count": 10}],
        "tertiary": [{"key": "权益无法兑换", "count": 8}],
        "service_type": [{"key": "业务类", "count": 7}, {"key": "体验类", "count": 3}],
        "biz_member_cluster": [{"key": "钻石会员", "count": 5}],
        "refund": [],
        "escalation": [],
        "daily": [
            {
                "date": "2026-03-01",
                "count": 10,
                "negative_count": 4,
                "negative_ratio": 0.4,
                "day_over_day_growth": 0,
                "is_matchday": False,
                "matchday": None,
                "top_primary": [{"key": "业务体验", "count": 10}],
                "top_secondary": [{"key": "权益使用", "count": 10}],
                "top_events": [],
                "top_tertiary": [{"key": "权益无法兑换", "count": 8}],
                "top_service_type": [{"key": "业务类", "count": 7}],
                "top_member_cluster": [{"key": "钻石会员", "count": 5}],
                "samples": [],
            }
        ],
        "anomalies": [],
        "unlabeled_analysis": {"unlabeled_total": 4},
        "schedule": {"status": "loaded", "source_name": "赛程.xlsx", "days": {}, "message": "已加载赛程文件 赛程.xlsx"},
        "top_tertiary_examples": [
            {
                "key": "权益无法兑换",
                "count": 8,
                "top_appeals": [{"key": "要求解决权益", "count": 3}],
                "top_customer_keywords": [{"key": "电视端", "count": 2}, {"key": "会员权益", "count": 1}],
                "top_cs_actions": [{"key": "记录并核查", "count": 2}],
                "top_cs_keywords": [{"key": "核查", "count": 2}, {"key": "反馈", "count": 1}],
                "samples": [
                    {
                        "appeal": "要求解决权益",
                        "cs_reply": "客服记录问题并提交核查，后续反馈处理结果。",
                        "operation_action": "不应展示的运营举措",
                        "biz_member_cluster": "不应展示的会员类型",
                        "latent_need": "不应展示的隐性需求",
                        "content_excerpt": '[{"发送方":"话务员","消息内容":"正在为您转接人工，请稍后..."},{"发送方":"用户","消息内容":"电视端无法使用已购买会员，要求尽快处理权益兑换问题"}]',
                    }
                ],
            }
        ],
        "source_files": [],
    }


class ReportTotalTests(unittest.TestCase):
    def test_distribution_insights_display_overall_total(self) -> None:
        insights = _distribution_insights(_result())

        self.assertIn("14", insights[0])
        self.assertNotIn("10 条已标注", insights[0])
        self.assertTrue(any("业务维度" in line for line in insights))
        text = "\n".join(insights)
        self.assertIn("业务体验（共10条，占比100.0%）", text)
        self.assertIn("权益使用（共10条，占比100.0%）", text)
        self.assertIn("权益无法兑换（共8条，占比100.0%）", text)
        self.assertNotIn("业务体验（10）", text)

    def test_markdown_header_uses_overall_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "report.md"
            render_markdown_report(_result(), output_path)

            content = output_path.read_text(encoding="utf-8")

        self.assertIn("总工单量：14 件", content)

    def test_report_omits_out_of_scope_modules_but_keeps_voice_and_cases(self) -> None:
        result = _result()
        result["query"] = {"section_focus": "full"}

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            html_path = tmp_path / "report.html"
            md_path = tmp_path / "report.md"
            render_html_report(result, html_path)
            render_markdown_report(result, md_path)

            validation = validate_html_report_for_focus(html_path, "full")
            content = html_path.read_text(encoding="utf-8") + "\n" + md_path.read_text(encoding="utf-8")

        self.assertTrue(validation.ok, validation.errors)
        for removed_title in [
            "本次查询",
            "口径说明",
            "分析要点",
            "展示方式",
            "计算说明",
            "运营举措与隐性诉求",
            "会员类型聚类",
            "问题链路归因",
            "情绪与风险分布",
            "服务类型与升级风险",
            "日趋势明细",
            "各级标签下钻关系",
            "隐性需求",
            "不应展示的运营举措",
            "不应展示的会员类型",
        ]:
            self.assertNotIn(removed_title, content)
        self.assertIn("样例原声与典型案例", content)
        self.assertNotIn("样例原声与原因研判", content)
        self.assertNotIn("#### 典型案例", content)
        self.assertIn("<td>8条</td>", content)
        self.assertIn("| 权益无法兑换 | 8条 |", content)
        self.assertIn("工单内容与客服回复总结", content)
        self.assertIn("客户诉求与关键词总结", content)
        self.assertIn("客服处理动作与关键词总结", content)
        self.assertNotIn("<td>共8条，占比", content)
        self.assertNotIn("| 权益无法兑换 | 共8条，占比", content)
        self.assertNotIn("高频诉求", content)
        self.assertNotIn("样例摘要 |", content)
        self.assertNotIn("消息内容", content)
        self.assertIn("用户围绕「权益无法兑换」主要反馈电视端或投屏观看权益受阻", content)

    def test_trend_insights_include_schedule_labels_and_business_dimension(self) -> None:
        result = _result()
        result["daily"][0]["is_matchday"] = True
        result["daily"][0]["matchday"] = {
            "match_summary": "第1轮 19:35 A队 vs B队",
            "rounds": ["第1轮"],
            "match_count": 1,
            "matches": [],
        }
        trend_view = {"days": result["daily"], "anomalies": [], "used_focus_window": False}

        text = "\n".join(_trend_insights(result, trend_view))

        self.assertIn("有比赛的是", text)
        self.assertIn("赛事日合计问题量", text)
        self.assertNotIn("已加载赛程文件", text)
        self.assertNotIn("赛事日标注", text)
        self.assertNotIn("当日一级/二级/三级热点", text)
        self.assertNotIn("峰值日业务热点", text)

    def test_anomaly_cards_show_all_days_sorted_by_growth_count_date(self) -> None:
        anomalies = [
            {
                "date": "2026-03-08",
                "count": 20,
                "day_over_day_growth": 0.8,
                "negative_ratio": 0.2,
                "top_primary": [{"key": "使用体验", "count": 10}],
                "top_secondary": [{"key": "播放问题", "count": 10}],
                "top_tertiary": [{"key": "卡顿", "count": 8}],
                "top_service_type": [{"key": "体验类", "count": 10}],
                "top_member_cluster": [{"key": "中超赛季包", "count": 6}],
            },
            {
                "date": "2026-03-06",
                "count": 10,
                "day_over_day_growth": 1.2,
                "negative_ratio": 0.3,
                "top_primary": [{"key": "业务体验", "count": 8}],
                "top_secondary": [{"key": "权益使用", "count": 8}],
                "top_tertiary": [{"key": "权益无法兑换", "count": 8}],
                "top_service_type": [{"key": "业务类", "count": 8}],
                "top_member_cluster": [{"key": "钻石会员", "count": 5}],
            },
            {
                "date": "2026-03-07",
                "count": 30,
                "day_over_day_growth": 1.2,
                "negative_ratio": 0.4,
                "top_primary": [{"key": "业务体验", "count": 20}],
                "top_secondary": [{"key": "计费争议", "count": 20}],
                "top_tertiary": [{"key": "自动续费不知情", "count": 20}],
                "top_service_type": [{"key": "业务类", "count": 20}],
                "top_member_cluster": [{"key": "足球通", "count": 12}],
            },
        ]

        html = _compact_anomaly_cards(anomalies)

        self.assertIn("日环比增长 ≥ 50%", html)
        self.assertIn("排名前三的异动节点", html)
        self.assertLess(html.index("2026-03-07"), html.index("2026-03-06"))
        self.assertLess(html.index("2026-03-06"), html.index("2026-03-08"))
        self.assertNotIn("service_time", html)
        self.assertNotIn("全部异动日", html)
        self.assertIn("主要一级问题", html)
        self.assertIn("业务热点", html)


if __name__ == "__main__":
    unittest.main()
