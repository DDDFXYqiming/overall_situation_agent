from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class MappingError(RuntimeError):
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING_PATH = PROJECT_ROOT / "es_mapping.json"


def _strip_field_meta(properties: dict[str, Any], field_catalog: dict[str, Any]) -> dict[str, Any]:
    runtime_properties: dict[str, Any] = {}
    for field, mapping in properties.items():
        if not isinstance(mapping, dict):
            runtime_properties[field] = mapping
            continue
        runtime_mapping = copy.deepcopy(mapping)
        meta = runtime_mapping.pop("meta", None)
        if meta is not None:
            field_catalog[field] = meta
        if isinstance(runtime_mapping.get("properties"), dict):
            nested_catalog: dict[str, Any] = {}
            runtime_mapping["properties"] = _strip_field_meta(runtime_mapping["properties"], nested_catalog)
            if nested_catalog:
                field_catalog.setdefault(field, {})["properties"] = nested_catalog
        runtime_properties[field] = runtime_mapping
    return runtime_properties


def _validate_index_mapping(mapping: dict[str, Any], path: Path) -> None:
    if not isinstance(mapping, dict):
        raise MappingError(f"ES mapping must be a JSON object: {path}")
    settings = mapping.get("settings")
    mappings = mapping.get("mappings")
    if not isinstance(settings, dict):
        raise MappingError(f"ES mapping missing settings object: {path}")
    if not isinstance(mappings, dict):
        raise MappingError(f"ES mapping missing mappings object: {path}")
    properties = mappings.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise MappingError(f"ES mapping missing non-empty mappings.properties: {path}")
    for field in (
        "service_time",
        "primary_labels",
        "secondary_labels",
        "tertiary_labels",
        "scene_emotion",
        "scene_service_type",
        "customer_key_appeal",
        "biz_member_cluster",
        "match_label",
    ):
        if field not in properties:
            raise MappingError(f"ES mapping missing required field [{field}]: {path}")


def load_mapping_document(path: Path | None = None) -> dict[str, Any]:
    mapping_path = path or DEFAULT_MAPPING_PATH
    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MappingError(f"ES mapping file not found: {mapping_path}") from exc
    except json.JSONDecodeError as exc:
        raise MappingError(f"ES mapping is not valid JSON: {mapping_path}: {exc}") from exc
    _validate_index_mapping(mapping, mapping_path)
    return mapping


@lru_cache(maxsize=4)
def load_index_mapping(path_text: str | None = None) -> dict[str, Any]:
    mapping_path = Path(path_text) if path_text else DEFAULT_MAPPING_PATH
    mapping = copy.deepcopy(load_mapping_document(mapping_path))
    mappings = mapping.setdefault("mappings", {})
    properties = mappings.get("properties") or {}
    field_catalog = dict((mappings.get("_meta") or {}).get("field_catalog") or {})
    mappings["properties"] = _strip_field_meta(properties, field_catalog)
    mappings.setdefault("_meta", {})["field_catalog"] = field_catalog
    _validate_index_mapping(mapping, mapping_path)
    return mapping


def mapping_properties(path: Path | None = None) -> dict[str, Any]:
    return copy.deepcopy(load_index_mapping(str(path) if path else None)["mappings"]["properties"])


def allowed_search_fields(path: Path | None = None) -> set[str]:
    fields: set[str] = set()
    for field, mapping in mapping_properties(path).items():
        fields.add(field)
        if isinstance(mapping, dict):
            subfields = mapping.get("fields")
            if isinstance(subfields, dict):
                for subfield in subfields:
                    fields.add(f"{field}.{subfield}")
    return fields
