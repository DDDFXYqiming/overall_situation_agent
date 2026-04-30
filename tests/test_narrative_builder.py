from __future__ import annotations

import json
import unittest

from overall_situation_agent.llm_client import LLMResponse
from overall_situation_agent.narrative_builder import NARRATIVE_KEYS, build_report_narratives


class _FakeLLM:
    enabled = True
    report_enabled = True
    report_timeout = 3
    report_max_retries = 0
    report_max_tokens = 321

    def __init__(self, response: LLMResponse):
        self.response = response
        self.kwargs = None

    def chat(self, messages, **kwargs):
        self.kwargs = kwargs
        return self.response


class _DisabledLLM:
    enabled = False
    report_enabled = False


class NarrativeBuilderTests(unittest.TestCase):
    def test_report_narratives_use_bounded_best_effort_llm_call(self) -> None:
        content = json.dumps({key: [f"{key} ok"] for key in NARRATIVE_KEYS}, ensure_ascii=False)
        llm = _FakeLLM(LLMResponse(content=content))

        narratives = build_report_narratives({"total": 10}, llm)

        self.assertEqual(narratives["executive_summary"], ["executive_summary ok"])
        self.assertEqual(llm.kwargs["timeout_seconds"], 3)
        self.assertEqual(llm.kwargs["max_retries"], 0)
        self.assertEqual(llm.kwargs["max_tokens"], 321)

    def test_report_narratives_fall_back_when_llm_is_unavailable(self) -> None:
        llm = _FakeLLM(LLMResponse(content="", used_fallback=True))

        with self.assertLogs("overall_situation_agent.narrative_builder", level="WARNING"):
            narratives = build_report_narratives({"total": 10}, llm)

        self.assertTrue(narratives["distribution_conclusion"])
        self.assertIn("本周期共纳入", narratives["distribution_conclusion"][0])

    def test_unlabeled_summary_is_separate_from_main_conclusions(self) -> None:
        result = {
            "total": 10,
            "total_with_unlabeled": 14,
            "primary": [{"key": "业务体验", "count": 10}],
            "secondary": [{"key": "权益使用", "count": 10}],
            "tertiary": [{"key": "权益无法兑换", "count": 8}],
            "unlabeled_analysis": {
                "unlabeled_total": 4,
                "emotion": [{"key": "愤怒", "count": 2}],
                "csp_name": [{"key": "咪咕视频APP", "count": 3}],
                "operation_action": [{"key": "足球通首月5折活动", "count": 2}],
                "latent_need": [{"key": "希望规则更清楚", "count": 2}],
                "customer_key_appeal": [{"key": "要求退费", "count": 2}],
                "has_refund_demand": [{"key": "是", "count": 1}],
                "has_escalation": [{"key": "是", "count": 1}],
            },
            "unlabeled_trend_analysis": {
                "unlabeled_total": 4,
                "daily": [
                    {"date": "2026-03-01", "count": 1, "negative_ratio": 0},
                    {"date": "2026-03-02", "count": 3, "negative_ratio": 0.5},
                ],
                "peak_day": {"date": "2026-03-02", "count": 3},
                "emotion_peak_day": {"date": "2026-03-02", "negative_ratio": 0.5},
            },
        }

        narratives = build_report_narratives(result, _DisabledLLM())

        main_text = "\n".join(narratives["distribution_conclusion"] + narratives["trend_conclusion"])
        unlabeled_text = "\n".join(narratives["unlabeled_distribution_summary"] + narratives["unlabeled_trend_summary"])
        self.assertNotIn("未标注一二三级标签", main_text)
        self.assertNotIn("一/二/三级标签未标注", main_text)
        self.assertIn("一/二/三级标签未标注", unlabeled_text)
        self.assertNotIn("TOP5", unlabeled_text)
        self.assertNotIn("典型样例", unlabeled_text)

    def test_main_narratives_use_total_with_unlabeled_as_overall_total(self) -> None:
        result = {
            "total": 10,
            "total_with_unlabeled": 14,
            "primary": [{"key": "业务体验", "count": 10}],
            "secondary": [{"key": "权益使用", "count": 10}],
            "tertiary": [{"key": "权益无法兑换", "count": 8}],
            "unlabeled_analysis": {"unlabeled_total": 4},
        }

        narratives = build_report_narratives(result, _DisabledLLM())

        self.assertIn("14", narratives["executive_summary"][0])
        self.assertIn("14", narratives["distribution_conclusion"][0])
        self.assertNotIn("10 条已标注", narratives["distribution_conclusion"][0])

    def test_fallback_narratives_include_business_and_matchday_context(self) -> None:
        result = {
            "total": 10,
            "total_with_unlabeled": 14,
            "primary": [{"key": "业务体验", "count": 10}],
            "secondary": [{"key": "权益使用", "count": 10}],
            "tertiary": [{"key": "权益无法兑换", "count": 8}],
            "service_type": [{"key": "业务类", "count": 7}, {"key": "体验类", "count": 3}],
            "biz_member_cluster": [{"key": "钻石会员", "count": 5}],
            "daily": [
                {
                    "date": "2026-03-07",
                    "count": 10,
                    "negative_ratio": 0.4,
                    "is_matchday": True,
                    "matchday": {"match_summary": "第1轮 A队 vs B队"},
                    "top_primary": [{"key": "业务体验", "count": 10}],
                    "top_secondary": [{"key": "权益使用", "count": 10}],
                    "top_tertiary": [{"key": "权益无法兑换", "count": 8}],
                    "top_service_type": [{"key": "业务类", "count": 7}],
                    "top_member_cluster": [{"key": "钻石会员", "count": 5}],
                }
            ],
            "schedule": {"status": "loaded", "source_name": "赛程.xlsx"},
            "unlabeled_analysis": {"unlabeled_total": 4},
        }

        narratives = build_report_narratives(result, _DisabledLLM())

        self.assertTrue(any("业务维度" in line for line in narratives["distribution_conclusion"]))
        trend_text = "\n".join(narratives["trend_conclusion"])
        self.assertIn("赛程.xlsx", trend_text)
        self.assertIn("赛事日标注", trend_text)
        self.assertIn("一级/二级/三级", trend_text)
        self.assertIn("业务热点", trend_text)


if __name__ == "__main__":
    unittest.main()
