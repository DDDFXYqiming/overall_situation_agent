from __future__ import annotations

import json
import unittest
from pathlib import Path

from overall_situation_agent.mapping_loader import allowed_search_fields, load_index_mapping
from overall_situation_agent.schema import index_mapping
from overall_situation_agent.template_executor import TemplateExecutor


class MappingAndTemplateTests(unittest.TestCase):
    def test_es_mapping_is_runtime_index_body(self) -> None:
        mapping = index_mapping()

        self.assertIn("settings", mapping)
        self.assertIn("mappings", mapping)
        self.assertIn("analysis", mapping["settings"])
        self.assertTrue(mapping["mappings"]["dynamic"])
        properties = mapping["mappings"]["properties"]
        for field in [
            "service_time",
            "primary_labels",
            "secondary_labels",
            "tertiary_labels",
            "scene_emotion",
            "scene_service_type",
            "customer_key_appeal",
            "biz_member_cluster",
            "match_label",
        ]:
            self.assertIn(field, properties)
            self.assertNotIn("meta", properties[field])
        self.assertIn("field_catalog", mapping["mappings"]["_meta"])
        self.assertEqual(properties["content"]["analyzer"], "migu_analyzer")
        self.assertEqual(properties["content"]["search_analyzer"], "migu_search_analyzer")

    def test_allowed_fields_are_derived_from_mapping(self) -> None:
        fields = allowed_search_fields()

        self.assertIn("customer_key_appeal", fields)
        self.assertIn("customer_key_appeal.keyword", fields)
        self.assertIn("营销活动匹配说明.keyword", fields)

    def test_all_templates_keep_flat_contract_and_parse(self) -> None:
        for path in Path("es_templates").glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(data), {"question", "description", "dsl"}, path.name)
            self.assertIsInstance(data["dsl"], dict, path.name)

    def test_runtime_template_renders_inclusive_end_date_as_exclusive_range(self) -> None:
        body = TemplateExecutor().render_with_dates(
            "90_runtime_overall_aggregations",
            start_date="2026-03-01",
            end_date="2026-03-31",
        )

        date_filter = body["query"]["bool"]["filter"][0]["range"]["service_time"]
        self.assertEqual(date_filter, {"gte": "2026-03-01", "lt": "2026-04-01"})
        self.assertIn("daily", body["aggs"])
        self.assertIn("top_tertiary_examples", body["aggs"])

    def test_template_without_dates_prunes_empty_range_to_match_all(self) -> None:
        body = TemplateExecutor().render_with_dates("90_runtime_total_with_unlabeled")

        self.assertEqual(body["query"], {"match_all": {}})


if __name__ == "__main__":
    unittest.main()
