from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def make_report_path(outputs_dir: Path, question: str) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    compact = re.sub(r"\s+", "", question)
    compact = re.sub(r"[^\w\u4e00-\u9fff-]", "", compact)
    slug = compact[:24] or "overall"
    return outputs_dir / f"overall_situation_{timestamp}_{slug}.html"


def normalize_report_path(outputs_dir: Path, requested: Path | None, question: str) -> Path:
    if requested is None:
        return make_report_path(outputs_dir, question)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    name = requested.name or make_report_path(outputs_dir, question).name
    if not name.lower().endswith(".html"):
        name = f"{name}.html"
    return outputs_dir / name
