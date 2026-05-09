from __future__ import annotations

import logging
from pathlib import Path

from .aggregations import run_overall_aggregations
from .config import Settings
from .es_client import create_es_client, ensure_index
from .import_state import (
    ImportManifest,
    build_import_manifest,
    build_import_state,
    load_import_state,
    save_import_state,
)
from .importer import import_excel_to_es
from .llm_client import OpenAICompatibleClient
from .markdown_renderer import render_markdown_report
from .narrative_builder import build_report_narratives
from .report import render_html_report
from .schedule_loader import enrich_result_with_schedule, load_schedule_context
from .validator import validate_html_report_for_focus, validate_report_result

logger = logging.getLogger(__name__)


class ImportResult(tuple):
    __slots__ = ()

    @property
    def count(self) -> int:
        return self[0]

    @property
    def imported(self) -> bool:
        return self[1]

    @property
    def message(self) -> str:
        return self[2]

    def __new__(cls, count: int, imported: bool, message: str) -> "ImportResult":
        return super().__new__(cls, (count, imported, message))


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


class OverallSituationAgent:
    """Single-purpose Agent for report section 一、整体情况."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.es = create_es_client(settings)
        self.llm = OpenAICompatibleClient(settings)

    def import_data(self, input_path: Path, recreate_index: bool = False) -> ImportResult:
        input_path = input_path.resolve()
        input_files = _input_files(input_path)
        if not input_files:
            return ImportResult(0, False, f"未找到可导入的 Excel 文件：{input_path}")

        cached_state = load_import_state(self.settings.import_state_file)
        if self.es.indices.exists(index=self.settings.es_index):
            current_count = int(self.es.count(index=self.settings.es_index).body.get("count", 0) or 0)
        else:
            current_count = 0

        state_matches_input = _state_matches_input(
            cached_state,
            input_path,
            input_files,
            self.settings.es_index,
        )
        if not recreate_index and current_count > 0 and state_matches_input:
            logger.info(
                "Skipping import for %s because the same source file is already loaded into %s",
                input_path,
                self.settings.es_index,
            )
            return ImportResult(
                current_count,
                False,
                f"检测到相同源文件已导入索引 [{self.settings.es_index}]，跳过重复导入。",
            )

        effective_recreate = recreate_index or bool(current_count > 0 and cached_state and not state_matches_input)
        if effective_recreate and not recreate_index:
            logger.info(
                "Recreating index %s because cached source differs from requested input %s",
                self.settings.es_index,
                input_path,
            )
        ensure_index(self.es, self.settings.es_index, recreate=effective_recreate)
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
        return ImportResult(
            total_count,
            True,
            f"已导入 {total_count} 条记录到索引 [{self.settings.es_index}]。{detail_text}",
        )

    def analyze(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        query_context: dict | None = None,
        schedule_input: Path | None = None,
    ) -> dict:
        ensure_index(self.es, self.settings.es_index, recreate=False)
        result = run_overall_aggregations(self.es, self.settings.es_index, start_date, end_date)
        result = enrich_result_with_schedule(result, load_schedule_context(schedule_input))
        if query_context:
            result["query"] = query_context
        result["narratives"] = build_report_narratives(result, self.llm)
        validation = validate_report_result(result)
        if not validation.ok:
            raise ValueError("聚合结果校验失败：" + "；".join(validation.errors))
        return result

    def generate_report(
        self,
        output_path: Path,
        start_date: str | None = None,
        end_date: str | None = None,
        query_context: dict | None = None,
        schedule_input: Path | None = None,
    ) -> Path:
        result = self.analyze(
            start_date=start_date,
            end_date=end_date,
            query_context=query_context,
            schedule_input=schedule_input,
        )
        path = render_html_report(result, output_path)
        render_markdown_report(result, path.with_suffix(".md"))
        section_focus = (query_context or {}).get("section_focus", "full")
        validation = validate_html_report_for_focus(path, section_focus=section_focus)
        if not validation.ok:
            raise ValueError("HTML 报告校验失败：" + "；".join(validation.errors))
        return path

    def run(
        self,
        input_path: Path,
        output_path: Path,
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
