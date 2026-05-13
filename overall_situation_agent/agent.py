from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .aggregations import run_overall_aggregations
from .config import Settings
from .es_client import SimpleElasticsearch, create_es_client, ensure_index
from .evidence import fetch_tertiary_evidence_for_labels, fetch_tertiary_top_evidence
from .import_state import (
    ImportManifest,
    build_import_manifest,
    build_import_state,
    load_import_state,
    save_import_state,
)
from .importer import import_excel_to_es
from .llm_client import OpenAICompatibleClient
from .logging_setup import setup_logging
from .markdown_renderer import render_markdown_report
from .narrative_builder import build_report_narratives
from .output_naming import make_report_path
from .report import render_html_report
from .schedule_loader import enrich_result_with_schedule, load_schedule_context
from .taxonomy import collect_md_tertiary_items
from .validator import validate_html_report_for_focus, validate_report_result

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportResult:
    count: int
    imported: bool
    message: str
    success: bool = True


def _input_files(input_path: Path) -> list[Path]:
    if input_path.is_dir():
        return sorted(
            [
                path
                for path in input_path.iterdir()
                if path.is_file()
                and path.suffix.lower() in {".xlsx", ".xlsm"}
                and not path.name.startswith("~$")
            ],
            key=lambda item: item.name.lower(),
        )
    return [input_path]


def _state_matches_input(
    cached_state: ImportManifest | object | None,
    input_path: Path,
    input_files: list[Path],
    es_index: str,
) -> bool:
    if not cached_state:
        return False
    if isinstance(cached_state, ImportManifest):
        return cached_state.matches(input_path, es_index) and cached_state.matches_files(input_files, es_index)
    return len(input_files) == 1 and bool(cached_state.matches(input_files[0], es_index))


def _annotate_md_evidence(evidence: dict[str, Any], md_items: list[dict[str, Any]]) -> dict[str, Any]:
    item_by_source = {str(item.get("source_key", "")).strip(): item for item in md_items}
    for label_data in evidence.get("labels", []):
        source_key = str(label_data.get("key", "")).strip()
        item = item_by_source.get(source_key)
        if not item:
            continue
        label_data["source_key"] = source_key
        label_data["key"] = item["key"]
        label_data["canonical_key"] = item["key"]
        label_data["primary_key"] = item["primary_key"]
        label_data["primary_count"] = item["primary_count"]
        label_data["count"] = item["count"]
        label_data["share"] = (int(item["count"]) / int(item["primary_count"])) if int(item["primary_count"]) else 0
    return evidence


class OverallSituationAgent:
    """Report orchestration plus reusable backend for CLI chat and API calls."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.es: SimpleElasticsearch = create_es_client(settings)
        self.llm = OpenAICompatibleClient(settings)
        setup_logging(settings.logs_dir)

    def import_data(self, input_path: Path, recreate_index: bool = False) -> ImportResult:
        input_path = input_path.resolve()
        if not input_path.exists():
            return ImportResult(0, False, f"输入路径不存在：{input_path}", success=False)

        input_files = _input_files(input_path)
        if not input_files:
            return ImportResult(0, False, f"未找到可导入的 Excel 文件：{input_path}", success=False)

        cached_state = load_import_state(self.settings.import_state_file)
        if self.es.indices.exists(index=self.settings.es_index):
            current_count = int(self.es.count(index=self.settings.es_index).body.get("count", 0) or 0)
        else:
            current_count = 0

        state_matches_input = _state_matches_input(cached_state, input_path, input_files, self.settings.es_index)
        if not recreate_index and current_count > 0 and state_matches_input:
            logger.info("Skipping import for %s because source is already loaded into %s", input_path, self.settings.es_index)
            return ImportResult(
                current_count,
                False,
                f"检测到相同源文件已导入索引 [{self.settings.es_index}]，跳过重复导入。",
            )

        effective_recreate = recreate_index or bool(current_count > 0 and cached_state and not state_matches_input)
        if effective_recreate and not recreate_index:
            logger.info("Recreating index %s because cached source differs from requested input %s", self.settings.es_index, input_path)

        ensure_index(self.es, self.settings.es_index, recreate=effective_recreate)
        if recreate_index:
            self.settings.import_state_file.unlink(missing_ok=True)

        states = []
        total_count = 0
        details = []
        for file_path in input_files:
            count = import_excel_to_es(
                self.es,
                self.settings.es_index,
                file_path,
                batch_size=self.settings.import_batch_size,
            )
            states.append(build_import_state(file_path, self.settings.es_index, count))
            total_count += count
            details.append(f"{file_path.name}: {count} 条")

        state = states[0] if len(states) == 1 else build_import_manifest(input_path, self.settings.es_index, states)
        save_import_state(self.settings.import_state_file, state)
        detail_text = "；".join(details)
        return ImportResult(total_count, True, f"已导入 {total_count} 条记录到索引 [{self.settings.es_index}]。{detail_text}")

    def analyze(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        query_context: dict[str, Any] | None = None,
        schedule_input: Path | None = None,
    ) -> dict[str, Any]:
        ensure_index(self.es, self.settings.es_index, recreate=False)

        logger.info("Running aggregations...")
        result = run_overall_aggregations(self.es, self.settings.es_index, start_date, end_date)
        result = enrich_result_with_schedule(result, load_schedule_context(schedule_input))
        if query_context:
            result["query"] = query_context

        logger.info("Fetching tertiary TOP evidence...")
        all_tertiary_total = sum(item.get("count", 0) for item in result.get("tertiary", []))
        result["tertiary_evidence"] = fetch_tertiary_top_evidence(
            self.es,
            self.settings.es_index,
            total_hits=result.get("total", 0),
            start_date=start_date,
            end_date=end_date,
            all_tertiary_total=all_tertiary_total,
        )

        md_items = collect_md_tertiary_items(result, top_primary=5, top_tertiary_per_primary=5)
        result["md_tertiary_items"] = md_items
        md_labels = [str(item.get("source_key", "")).strip() for item in md_items if str(item.get("source_key", "")).strip()]
        if md_labels:
            result["tertiary_evidence_md"] = _annotate_md_evidence(
                fetch_tertiary_evidence_for_labels(
                    self.es,
                    self.settings.es_index,
                    total_hits=result.get("total", 0),
                    labels=md_labels,
                    start_date=start_date,
                    end_date=end_date,
                    all_tertiary_total=all_tertiary_total,
                ),
                md_items,
            )
        else:
            result["tertiary_evidence_md"] = {
                "labels": [],
                "sampling": {"per_label": 0, "total_hits": result.get("total", 0)},
            }

        logger.info("Building narratives...")
        result["narratives"] = build_report_narratives(result, self.llm)

        validation = validate_report_result(result)
        if not validation.ok:
            raise ValueError("聚合结果校验失败：" + "；".join(validation.errors))
        return result

    def generate_report(
        self,
        output_path: Path | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        query_context: dict[str, Any] | None = None,
        schedule_input: Path | None = None,
    ) -> Path:
        self.settings.outputs_dir.mkdir(parents=True, exist_ok=True)
        if output_path is None:
            output_path = make_report_path(self.settings.outputs_dir)

        result = self.analyze(
            start_date=start_date,
            end_date=end_date,
            query_context=query_context,
            schedule_input=schedule_input,
        )

        logger.info("Rendering HTML report...")
        html_path = render_html_report(result, output_path)
        logger.info("Rendering Markdown report...")
        render_markdown_report(result, html_path.with_suffix(".md"))

        section_focus = (query_context or {}).get("section_focus", "full")
        validation = validate_html_report_for_focus(html_path, section_focus=section_focus)
        if not validation.ok:
            raise ValueError("HTML 报告校验失败：" + "；".join(validation.errors))

        logger.info("Report generated: %s", html_path)
        return html_path

    def run(
        self,
        input_path: Path,
        output_path: Path | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        recreate_index: bool = False,
        schedule_input: Path | None = None,
    ) -> Path:
        self.import_data(input_path=input_path, recreate_index=recreate_index)
        return self.generate_report(
            output_path=output_path,
            start_date=start_date,
            end_date=end_date,
            schedule_input=schedule_input,
        )
