from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any


class TemplateError(RuntimeError):
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE_DIR = PROJECT_ROOT / "es_templates"
PLACEHOLDER_RE = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
FULL_PLACEHOLDER_RE = re.compile(r"^{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}$")


@dataclass(frozen=True)
class QueryTemplate:
    id: str
    question: str
    description: str
    visibility: str
    dsl: dict[str, Any]
    path: Path

    @property
    def placeholders(self) -> set[str]:
        raw = json.dumps(self.dsl, ensure_ascii=False)
        return set(PLACEHOLDER_RE.findall(raw))


def _validate_template_item(data: dict[str, Any], path: Path, template_id: str) -> QueryTemplate:
    allowed_keys = {"id", "question", "description", "visibility", "dsl"}
    unknown = set(data) - allowed_keys
    if unknown:
        raise TemplateError(f"Template has unsupported keys at {path} [{template_id}]: {', '.join(sorted(unknown))}")
    if not isinstance(data.get("question"), str) or not data["question"].strip():
        raise TemplateError(f"Template question must be a non-empty string: {path} [{template_id}]")
    if not isinstance(data.get("description"), str) or not data["description"].strip():
        raise TemplateError(f"Template description must be a non-empty string: {path} [{template_id}]")
    if not isinstance(data.get("dsl"), dict) or not data["dsl"]:
        raise TemplateError(f"Template dsl must be a non-empty object: {path} [{template_id}]")
    visibility = data.get("visibility")
    if visibility is None:
        visibility = "runtime" if template_id.startswith("90_runtime_") else "llm"
    if visibility not in {"llm", "runtime"}:
        raise TemplateError(f"Template visibility must be llm or runtime: {path} [{template_id}]")
    try:
        normalized_id = str(template_id)
    except Exception as exc:  # pragma: no cover - defensive only
        raise TemplateError(f"Template id is invalid: {path} [{template_id}]") from exc
    return QueryTemplate(
        id=normalized_id,
        question=data["question"],
        description=data["description"],
        visibility=visibility,
        dsl=data["dsl"],
        path=path,
    )


def _load_templates_from_file(path: Path) -> list[QueryTemplate]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TemplateError(f"Template is not valid JSON: {path}: {exc}") from exc
    keys = set(data)
    if keys == {"question", "description", "dsl"}:
        return [_validate_template_item(data, path, path.stem)]
    if "templates" not in data:
        raise TemplateError(f"Template file must be a flat template or contain templates[]: {path}")
    if not isinstance(data["templates"], list) or not data["templates"]:
        raise TemplateError(f"Template file templates must be a non-empty list: {path}")
    templates = []
    for idx, item in enumerate(data["templates"]):
        if not isinstance(item, dict):
            raise TemplateError(f"Template entry must be an object: {path} [{idx}]")
        template_id = item.get("id")
        if not isinstance(template_id, str) or not template_id.strip():
            raise TemplateError(f"Combined template entry must include a non-empty id: {path} [{idx}]")
        templates.append(_validate_template_item(item, path, template_id.strip()))
    return templates


class TemplateRegistry:
    def __init__(self, template_dir: Path | None = None):
        self.template_dir = template_dir or DEFAULT_TEMPLATE_DIR
        self.templates = self._load_templates()

    def _load_templates(self) -> dict[str, QueryTemplate]:
        if not self.template_dir.exists():
            raise TemplateError(f"Template directory not found: {self.template_dir}")
        templates: dict[str, QueryTemplate] = {}
        for path in sorted(self.template_dir.glob("*.json")):
            for template in _load_templates_from_file(path):
                if template.id in templates:
                    raise TemplateError(f"Duplicate template id: {template.id}")
                templates[template.id] = template
        if not templates:
            raise TemplateError(f"No JSON templates found under {self.template_dir}")
        return templates

    def get(self, template_id: str) -> QueryTemplate:
        try:
            return self.templates[template_id]
        except KeyError as exc:
            raise TemplateError(f"Unknown template id: {template_id}") from exc

    def render(self, template_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        template = self.get(template_id)
        params = params or {}
        missing = sorted(name for name in template.placeholders if name not in params)
        if missing:
            raise TemplateError(f"Template [{template_id}] missing params: {', '.join(missing)}")
        rendered = _render_value(copy.deepcopy(template.dsl), params)
        return _normalize_search_body(rendered)

    def list_for_llm(self, limit: int = 40) -> list[dict[str, str]]:
        items = []
        for template in self.templates.values():
            if template.visibility != "llm":
                continue
            items.append(
                {
                    "template_id": template.id,
                    "question": template.question,
                    "description": template.description,
                    "params": ", ".join(sorted(template.placeholders)),
                }
            )
            if len(items) >= limit:
                break
        return items


def default_date_params(start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"start_date": start_date, "end_date": end_date}
    if end_date:
        end_dt = datetime.fromisoformat(end_date[:10]) + timedelta(days=1)
        params["end_date_exclusive"] = end_dt.strftime("%Y-%m-%d")
    else:
        params["end_date_exclusive"] = None
    return params


def _render_value(value: Any, params: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _render_value(item, params) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_value(item, params) for item in value]
    if isinstance(value, str):
        full = FULL_PLACEHOLDER_RE.match(value)
        if full:
            return copy.deepcopy(params.get(full.group(1)))

        def repl(match: re.Match[str]) -> str:
            replacement = params.get(match.group(1))
            return "" if replacement is None else str(replacement)

        return PLACEHOLDER_RE.sub(repl, value)
    return value


def _drop_empty(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {key: _drop_empty(item) for key, item in value.items()}
        cleaned = {key: item for key, item in cleaned.items() if item is not None}
        if (
            "range" in cleaned
            and isinstance(cleaned["range"], dict)
            and "field" not in cleaned["range"]
            and "ranges" not in cleaned["range"]
        ):
            cleaned["range"] = {
                field: body
                for field, body in cleaned["range"].items()
                if isinstance(body, dict) and body
            }
            if not cleaned["range"]:
                return None
        if "terms" in cleaned and isinstance(cleaned["terms"], dict):
            terms = cleaned["terms"]
            if "include" in terms and terms["include"] in (None, [], ""):
                terms.pop("include", None)
        if "bool" in cleaned and isinstance(cleaned["bool"], dict):
            bool_body = cleaned["bool"]
            for key in ("filter", "must", "should", "must_not"):
                if isinstance(bool_body.get(key), list):
                    bool_body[key] = [item for item in bool_body[key] if item is not None]
                    if not bool_body[key]:
                        bool_body.pop(key, None)
            if not bool_body:
                return {"match_all": {}}
        return cleaned
    if isinstance(value, list):
        cleaned_items = []
        for item in value:
            cleaned_item = _drop_empty(item)
            if cleaned_item is not None:
                cleaned_items.append(cleaned_item)
        return cleaned_items
    if value == "":
        return None
    return value


def _normalize_search_body(body: dict[str, Any]) -> dict[str, Any]:
    cleaned = _drop_empty(body)
    if not isinstance(cleaned, dict):
        raise TemplateError("Rendered template did not produce an object")
    query = cleaned.get("query")
    if isinstance(query, dict) and query == {"bool": {}}:
        cleaned["query"] = {"match_all": {}}
    if "query" not in cleaned and ("aggs" in cleaned or "aggregations" in cleaned):
        cleaned["query"] = {"match_all": {}}
    return cleaned


@lru_cache(maxsize=4)
def get_default_registry(template_dir_text: str | None = None) -> TemplateRegistry:
    return TemplateRegistry(Path(template_dir_text) if template_dir_text else DEFAULT_TEMPLATE_DIR)
