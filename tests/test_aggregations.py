from __future__ import annotations

import unittest

from overall_situation_agent.aggregations import normalize_aggregations


def _terms(*pairs: tuple[str, int]) -> dict:
    return {"buckets": [{"key": key, "doc_count": count} for key, count in pairs]}


def _top_hits() -> dict:
    return {"hits": {"hits": []}}


class AggregationNormalizeTests(unittest.TestCase):
    def test_normalize_aggregations_includes_new_header_clusters(self) -> None:
        response = {
            "hits": {"total": {"value": 3}},
            "aggregations": {
                "period_min": {"value_as_string": "2026-03-01"},
                "period_max": {"value_as_string": "2026-03-02"},
                "primary": _terms(("业务体验", 3)),
                "secondary": _terms(("权益使用", 3)),
                "tertiary": _terms(("权益无法兑换", 2)),
                "emotion": _terms(("愤怒", 2)),
                "service_type": _terms(("投诉", 3)),
                "province": _terms(("辽宁", 1)),
                "event": _terms(("中超", 3)),
                "source_file": _terms(("sample.xlsx", 3)),
                "refund": _terms(("是", 1)),
                "escalation": _terms(("否", 2)),
                "label_group": _terms(("中超", 3)),
                "insight_dimension": _terms(("用得亏", 2)),
                "customer_key_appeal": _terms(("要求退费", 2)),
                "cs_key_action": _terms(("解释规则", 2)),
                "operation_action": _terms(("足球通首月5折活动", 2)),
                "biz_member_cluster": _terms(("中超赛季包", 2)),
                "marketing_activity_page": _terms(("活动页A", 2)),
                "marketing_activity_match_status": _terms(("已匹配", 2)),
                "marketing_activity_match_keywords": _terms(("首月5折", 2)),
                "gender": _terms(("男", 2)),
                "age_ranges": {"buckets": [{"key": "26-35", "doc_count": 2}]},
                "time_period": _terms(("上午", 2)),
                "match_label": _terms(("2026-03-01 A队 vs B队", 2)),
                "avg_duration_minutes": {"value": 30.0},
                "primary_secondary": {
                    "buckets": [{"key": "业务体验", "doc_count": 3, "secondary": _terms(("权益使用", 3))}]
                },
                "primary_secondary_tertiary": {
                    "buckets": [
                        {
                            "key": "业务体验",
                            "doc_count": 3,
                            "secondary": {
                                "buckets": [
                                    {"key": "权益使用", "doc_count": 3, "tertiary": _terms(("权益无法兑换", 2))}
                                ]
                            },
                        }
                    ]
                },
                "daily": {
                    "buckets": [
                        {
                            "key_as_string": "2026-03-01",
                            "doc_count": 3,
                            "negative": {"doc_count": 2},
                            "top_primary": _terms(("业务体验", 3)),
                            "top_secondary": _terms(("权益使用", 3)),
                            "top_tertiary": _terms(("权益无法兑换", 2)),
                            "top_service_type": _terms(("投诉", 3)),
                            "top_member_cluster": _terms(("中超赛季包", 2)),
                            "top_events": _terms(("中超", 3)),
                            "top_operations": _terms(("足球通首月5折活动", 2)),
                            "top_matches": _terms(("2026-03-01 A队 vs B队", 2)),
                            "sample_hits": _top_hits(),
                        }
                    ]
                },
                "top_tertiary_examples": {
                    "buckets": [
                        {
                            "key": "权益无法兑换",
                            "doc_count": 2,
                            "top_appeals": _terms(("要求退费", 2)),
                            "sample": _top_hits(),
                        }
                    ]
                },
                "operation_need_examples": {"buckets": []},
                "member_cluster_examples": {"buckets": []},
                "latent_need_examples": {"buckets": []},
            },
        }

        result = normalize_aggregations(response, "2026-03-01", "2026-03-02")

        self.assertEqual(result["label_group"], [{"key": "中超", "count": 3}])
        self.assertEqual(result["customer_key_appeal"][0]["key"], "要求退费")
        self.assertEqual(result["cs_key_action"][0]["key"], "解释规则")
        self.assertEqual(result["marketing_activity_page"][0]["key"], "活动页A")
        self.assertEqual(result["marketing_activity_match_status"][0]["key"], "已匹配")
        self.assertEqual(result["marketing_activity_match_keywords"][0]["key"], "首月5折")
        self.assertEqual(result["age_ranges"], [{"key": "26-35", "count": 2}])
        self.assertEqual(result["gender"], [{"key": "男", "count": 2}])
        self.assertEqual(result["daily"][0]["top_primary"], [{"key": "业务体验", "count": 3}])
        self.assertEqual(result["daily"][0]["top_secondary"], [{"key": "权益使用", "count": 3}])
        self.assertEqual(result["daily"][0]["top_service_type"], [{"key": "投诉", "count": 3}])
        self.assertEqual(result["daily"][0]["top_member_cluster"], [{"key": "中超赛季包", "count": 2}])


if __name__ == "__main__":
    unittest.main()
