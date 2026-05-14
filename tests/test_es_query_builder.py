import unittest
from types import SimpleNamespace

from overall_situation_agent.evidence import build_tertiary_evidence_package, clean_evidence_text, dynamic_samples_per_label
from overall_situation_agent.es_query_builder import ESQueryBuilder


class ESQueryBuilderDeterministicIntentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = ESQueryBuilder(
            es=SimpleNamespace(),
            index_name="test-index",
            llm=SimpleNamespace(enabled=False),
            max_size=100,
        )

    def test_top_tertiary_cause_query_uses_required_fields(self) -> None:
        intent = self.builder.build_deterministic_intent(
            "按数量排序最多的五个三级标签是哪些，并结合工单内容、处理意见、客户诉求和客服处理动作分析为什么这些最多"
        )

        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent["metadata"]["intent_type"], "tertiary_top_cause_analysis")
        agg = intent["query"]["aggs"]["top_tertiary_cause_analysis"]
        self.assertEqual(agg["terms"]["field"], "tertiary_labels")
        self.assertEqual(agg["terms"]["size"], 5)

        for field in [
            "content",
            "cs_reply",
            "customer_key_appeal",
            "customer_keywords",
            "cs_key_action",
            "cs_keywords",
        ]:
            self.assertIn(field, intent["expected_fields"])

    def test_primary_scoped_tertiary_distribution_keeps_primary_denominator(self) -> None:
        intent = self.builder.build_deterministic_intent(
            "一级标签业务体验下面的三级标签退订困难/自动续费争议的数量和占该一级问题比例是多少？"
        )

        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent["metadata"]["template_id"], "02_primary_tertiary_title_count")
        self.assertEqual(intent["metadata"]["template_params"]["primary_label"], "业务体验")
        self.assertEqual(intent["metadata"]["template_params"]["tertiary_label"], "退订困难/自动续费争议")
        aggs = intent["query"]["aggs"]
        self.assertEqual(aggs["primary_total"]["filter"], {"term": {"primary_labels": "业务体验"}})
        self.assertEqual(
            aggs["tertiary_count"]["filter"]["bool"]["must"],
            [
                {"term": {"primary_labels": "业务体验"}},
                {"term": {"tertiary_labels": "退订困难/自动续费争议"}},
            ],
        )

        summary = self.builder.summarize_results(
            {
                "hits_total": 1144,
                "hits": [],
                "aggregations": {
                    "tertiary_distribution": {
                        "buckets": [
                            {"key": "退订困难/自动续费争议", "doc_count": 539},
                        ]
                    }
                },
            }
        )

        terms = summary["aggregations"][0]
        self.assertEqual(terms["share_denominator"], 1144)
        self.assertEqual(terms["items"][0]["share"], round(539 / 1144, 4))

    def test_dynamic_sample_size_matches_expected_data_scale(self) -> None:
        self.assertEqual(dynamic_samples_per_label(2_000), 24)
        self.assertEqual(dynamic_samples_per_label(10_000), 48)
        self.assertEqual(dynamic_samples_per_label(30_000), 80)

    def test_evidence_package_fetches_raw_source_fields_and_cleans_dialog_json(self) -> None:
        es = _FakeES(total=30_000)
        package = build_tertiary_evidence_package(es, "idx", top_n=5)

        self.assertEqual(package["samples_per_label"], 80)
        self.assertEqual(len(package["items"]), 5)
        sample_query = es.search_bodies[1]
        self.assertEqual(sample_query["size"], 80)
        for field in [
            "content",
            "cs_reply",
            "customer_key_appeal",
            "customer_keywords",
            "cs_key_action",
            "cs_keywords",
        ]:
            self.assertIn(field, sample_query["_source"])

        sample = package["items"][0]["samples"][0]
        self.assertNotIn("消息内容", sample["content"])
        self.assertNotIn("发送方", sample["content"])
        self.assertIn("用户要求退订并退款", sample["content"])

    def test_fallback_summary_for_evidence_package_contains_top5_and_structured_clues(self) -> None:
        es = _FakeES(total=2_000)
        llm = SimpleNamespace(enabled=False)
        builder = ESQueryBuilder(es=es, index_name="idx", llm=llm, max_size=100)
        intent = builder.build_deterministic_intent("三级标签前五为什么最多")
        assert intent is not None

        results = builder.execute_intent(intent)
        parsed = builder.parse_results(results, intent)
        summary = builder.summarize_results(parsed)
        answer = builder.analyze_results("三级标签前五为什么最多", parsed, intent, result_summary=summary)

        self.assertIn("数量最多的五个三级标签", answer)
        self.assertIn("标签1", answer)
        self.assertIn("客户关键诉求", answer)
        self.assertIn("客服关键处理动作", answer)


class _FakeResponse:
    def __init__(self, body):
        self.body = body


class _FakeIndices:
    def exists(self, index: str) -> bool:
        return True


class _FakeES:
    def __init__(self, total: int):
        self.total = total
        self.indices = _FakeIndices()
        self.search_bodies = []

    def search(self, index: str, body: dict):
        self.search_bodies.append(body)
        aggs = body.get("aggs", {})
        if "top_tertiary" in aggs:
            return _FakeResponse(
                {
                    "hits": {"total": {"value": self.total}},
                    "aggregations": {
                        "tertiary_total": {"value": self.total},
                        "top_tertiary": {
                            "buckets": [
                                {"key": f"标签{idx}", "doc_count": max(1, self.total // (idx + 4))}
                                for idx in range(1, 6)
                            ]
                        },
                    },
                }
            )
        size = int(body.get("size") or 0)
        source = {
            "service_time": "2026-03-01",
            "tertiary_labels": "标签1",
            "scene_service_type": "投诉",
            "scene_emotion": "不满",
            "content": '[{"发送方":"话务员","消息内容":"正在为您转接人工，请稍后..."},{"发送方":"用户","消息内容":"用户要求退订并退款，电视端无法观看会员权益"}]',
            "cs_reply": "客服解释规则并提交核查，告知用户等待处理。",
            "customer_key_appeal": "要求退订退款",
            "customer_keywords": ["退订", "退款"],
            "cs_key_action": "解释规则并提交核查",
            "cs_keywords": ["解释", "核查"],
        }
        return _FakeResponse(
            {
                "hits": {
                    "total": {"value": size},
                    "hits": [{"_source": source} for _ in range(size)],
                },
                "aggregations": {
                    "top_customer_appeals": {"buckets": [{"key": "要求退订退款", "doc_count": 10}]},
                    "top_customer_keywords": {"buckets": [{"key": "退款", "doc_count": 8}]},
                    "top_cs_actions": {"buckets": [{"key": "解释规则并提交核查", "doc_count": 7}]},
                    "top_cs_keywords": {"buckets": [{"key": "核查", "doc_count": 6}]},
                },
            }
        )


if __name__ == "__main__":
    unittest.main()
