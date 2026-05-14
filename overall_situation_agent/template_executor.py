from __future__ import annotations

from typing import Any

from .es_client import SimpleElasticsearch
from .mapping_loader import allowed_search_fields
from .template_registry import TemplateRegistry, default_date_params, get_default_registry


class TemplateSafetyError(RuntimeError):
    pass


TOP_LEVEL_SEARCH_KEYS = {"query", "aggs", "aggregations", "size", "sort", "_source", "track_total_hits", "from", "timeout"}
BANNED_SEARCH_KEYS = {
    "script",
    "script_fields",
    "runtime_mappings",
    "suggest",
    "profile",
    "rescore",
    "pit",
    "search_after",
    "collapse",
    "delete",
    "update",
    "bulk",
    "indices",
    "query_string",
    "simple_query_string",
}
FIELD_KEYS = {"field"}
FIELD_CLAUSES = {"match", "match_phrase", "term", "terms", "range", "wildcard", "prefix"}


class TemplateExecutor:
    def __init__(
        self,
        registry: TemplateRegistry | None = None,
        allowed_fields: set[str] | None = None,
    ):
        self.registry = registry or get_default_registry()
        self.allowed_fields = allowed_fields or allowed_search_fields()

    def render(
        self,
        template_id: str,
        params: dict[str, Any] | None = None,
        *,
        validate: bool = True,
    ) -> dict[str, Any]:
        body = self.registry.render(template_id, params)
        if validate:
            self.validate_search_body(body)
        return body

    def render_with_dates(
        self,
        template_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        params: dict[str, Any] | None = None,
        *,
        validate: bool = True,
    ) -> dict[str, Any]:
        merged = default_date_params(start_date, end_date)
        merged.update(params or {})
        return self.render(template_id, merged, validate=validate)

    def search(
        self,
        es: SimpleElasticsearch,
        index_name: str,
        template_id: str,
        params: dict[str, Any] | None = None,
    ):
        body = self.render(template_id, params)
        return es.search(index=index_name, body=body)

    def search_with_dates(
        self,
        es: SimpleElasticsearch,
        index_name: str,
        template_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        params: dict[str, Any] | None = None,
    ):
        body = self.render_with_dates(template_id, start_date, end_date, params)
        return es.search(index=index_name, body=body)

    def validate_search_body(self, body: dict[str, Any]) -> None:
        unknown = set(body) - TOP_LEVEL_SEARCH_KEYS
        if unknown:
            raise TemplateSafetyError("Template DSL has unsupported top-level keys: " + ", ".join(sorted(unknown)))
        if not any(key in body for key in ("query", "aggs", "aggregations")):
            raise TemplateSafetyError("Template DSL must include query or aggs/aggregations")
        self._validate_node(body)

    def _validate_node(self, node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_text = str(key)
                if key_text in BANNED_SEARCH_KEYS or key_text.startswith("_") and key_text not in {"_source", "_count", "_key"}:
                    raise TemplateSafetyError(f"Template DSL contains banned key: {key_text}")
                if key_text in FIELD_KEYS:
                    self._require_allowed_field(value)
                if key_text in FIELD_CLAUSES and isinstance(value, dict):
                    if "field" in value:
                        self._require_allowed_field(value["field"])
                    else:
                        for field in value:
                            if field not in {"boost", "query"}:
                                self._require_allowed_field(field)
                if key_text == "_source":
                    self._validate_source(value)
                if key_text == "sort":
                    self._validate_sort(value)
                self._validate_node(value)
        elif isinstance(node, list):
            for item in node:
                self._validate_node(item)

    def _validate_source(self, value: Any) -> None:
        if value in (None, True, False):
            return
        if not isinstance(value, list):
            raise TemplateSafetyError("_source must be a field list or boolean")
        for field in value:
            self._require_allowed_field(field)

    def _validate_sort(self, value: Any) -> None:
        if value is None:
            return
        if not isinstance(value, list):
            raise TemplateSafetyError("sort must be a list")
        for item in value:
            if isinstance(item, str):
                self._require_allowed_field(item)
            elif isinstance(item, dict):
                for field in item:
                    self._require_allowed_field(field)
            else:
                raise TemplateSafetyError("sort contains unsupported element")

    def _require_allowed_field(self, field: Any) -> None:
        if not isinstance(field, str) or not self._is_allowed_field(field):
            raise TemplateSafetyError(f"Field is not declared in es_mapping.json: {field}")

    def _is_allowed_field(self, field: str) -> bool:
        if field in self.allowed_fields:
            return True
        if field.endswith(".keyword") and field[:-8] in self.allowed_fields:
            return True
        return False
