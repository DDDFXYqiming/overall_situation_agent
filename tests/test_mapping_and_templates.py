from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from overall_situation_agent.mapping_loader import allowed_search_fields, load_index_mapping
from overall_situation_agent.schema import index_mapping
from overall_situation_agent.template_executor import TemplateExecutor
from overall_situation_agent.template_registry import TemplateRegistry


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

    def test_combined_templates_parse_and_keep_unique_ids(self) -> None:
        paths = sorted(Path("es_templates").glob("*.json"))
        self.assertEqual(
            [path.name for path in paths],
            [
                "00_common.json",
                "01_distribution.json",
                "02_primary_modules.json",
                "03_trend_anomaly.json",
                "90_runtime_report.json",
            ],
        )

        seen: set[str] = set()
        for path in paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("templates", data, path.name)
            self.assertIsInstance(data["templates"], list, path.name)
            for item in data["templates"]:
                self.assertEqual(set(item), {"id", "visibility", "question", "description", "dsl"}, item)
                self.assertNotIn(item["id"], seen)
                seen.add(item["id"])
                self.assertIn(item["visibility"], {"llm", "runtime"})
                self.assertIsInstance(item["dsl"], dict, item["id"])

        self.assertEqual(len(seen), 30)

    def test_legacy_flat_template_files_are_still_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy_template.json"
            path.write_text(
                json.dumps(
                    {
                        "question": "2026年3月总服务量是多少？",
                        "description": "旧三键模板兼容性测试。",
                        "dsl": {"query": {"match_all": {}}},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            registry = TemplateRegistry(Path(tmp))

        self.assertIn("legacy_template", registry.templates)
        self.assertEqual(registry.templates["legacy_template"].visibility, "llm")

    def test_runtime_templates_are_hidden_from_llm_listing(self) -> None:
        listed = TemplateRegistry().list_for_llm()

        self.assertTrue(listed)
        self.assertFalse(any(item["template_id"].startswith("90_runtime_") for item in listed))
        self.assertIn("01_distribution_header_total_service_count", {item["template_id"] for item in listed})

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
