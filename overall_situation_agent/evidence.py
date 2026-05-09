from __future__ import annotations

import json
import re
from typing import Any

from .es_client import SimpleElasticsearch


EVIDENCE_SOURCE_FIELDS = [
    "service_time",
    "tertiary_labels",
    "scene_service_type",
    "scene_emotion",
    "content",
    "cs_reply",
    "customer_key_appeal",
    "customer_keywords",
    "cs_key_action",
    "cs_keywords",
]

CONTENT_LIMIT = 300
CS_REPLY_LIMIT = 220
STRUCTURED_LIMIT = 120
MAX_EVIDENCE_PAYLOAD_CHARS = 850_000
MIN_SAMPLES_PER_LABEL = 12
DEFAULT_TOP_N = 5

RAW_DIALOG_MARKERS = ("消息内容", "发送方", "[{", "{'")
BOILERPLATE_MARKERS = (
    "正在为您转接人工",
    "当前人工MM有点忙",
    "请稍后",
    "请耐心等待",
    "您好，很高兴为您服务",
    "请问有什么可以帮到您",
    "请您稍等",
    "人工客服排队",
)
EMPTY_EXCLUDE = ["", "无", "无明确", "未知", "不适用", "{}", "[]"]


def clean_evidence_text(value: Any, limit: int, *, prefer_user_messages: bool = False) -> str:
    if isinstance(value, (list, tuple, set)):
        text = "、".join(str(item).strip() for item in value if str(item).strip())
    else:
        text = "" if value is None else str(value).strip()
    if not text:
        return ""

    messages = _extract_messages(text, prefer_user_messages=prefer_user_messages)
    if messages:
        text = "；".join(messages)

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[A-Za-z0-9]{18,}", "", text)
    text = re.sub(r"(?<!\d)\d{11,}(?!\d)", "", text)
    for marker in BOILERPLATE_MARKERS:
        text = text.replace(marker, "")
    text = text.strip(" ;；,，。")
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "..."
    return text


def build_tertiary_evidence_package(
    es: SimpleElasticsearch,
    index_name: str,
    base_query: dict[str, Any] | None = None,
    *,
    top_n: int = DEFAULT_TOP_N,
    samples_per_label: int | None = None,
) -> dict[str, Any]:
    query = base_query or {"match_all": {}}
    top_response = es.search(
        index=index_name,
        body={
            "size": 0,
            "track_total_hits": True,
            "query": query,
            "aggs": {
                "top_tertiary": {"terms": {"field": "tertiary_labels", "size": top_n}},
                "tertiary_total": {"value_count": {"field": "tertiary_labels"}},
            },
        },
    ).body
    doc_total = _total_hits(top_response)
    tertiary_total = int((top_response.get("aggregations", {}).get("tertiary_total") or {}).get("value") or 0)
    top_buckets = (top_response.get("aggregations", {}).get("top_tertiary") or {}).get("buckets", [])
    requested_samples = samples_per_label or dynamic_samples_per_label(doc_total or tertiary_total, top_n=top_n)

    items = []
    denominator = tertiary_total or sum(int(bucket.get("doc_count", 0) or 0) for bucket in top_buckets) or 1
    for bucket in top_buckets[:top_n]:
        label = str(bucket.get("key") or "").strip()
        if not label:
            continue
        label_count = int(bucket.get("doc_count", 0) or 0)
        label_query = _and_filter(query, {"term": {"tertiary_labels": label}})
        label_sample_size = max(1, min(requested_samples, label_count or requested_samples))
        sample_response = es.search(
            index=index_name,
            body={
                "size": label_sample_size,
                "track_total_hits": True,
                "query": label_query,
                "_source": EVIDENCE_SOURCE_FIELDS,
                "sort": [{"service_time": {"order": "desc"}}],
                "aggs": {
                    "top_customer_appeals": _terms("customer_key_appeal.keyword", 8),
                    "top_customer_keywords": _terms("customer_keywords", 10),
                    "top_cs_actions": _terms("cs_key_action.keyword", 8),
                    "top_cs_keywords": _terms("cs_keywords", 10),
                },
            },
        ).body
        aggs = sample_response.get("aggregations", {})
        items.append(
            {
                "key": label,
                "count": label_count,
                "share": round(label_count / denominator, 4) if denominator else 0,
                "top_appeals": _bucket_list(aggs.get("top_customer_appeals", {})),
                "top_customer_appeals": _bucket_list(aggs.get("top_customer_appeals", {})),
                "top_customer_keywords": _bucket_list(aggs.get("top_customer_keywords", {})),
                "top_cs_actions": _bucket_list(aggs.get("top_cs_actions", {})),
                "top_cs_keywords": _bucket_list(aggs.get("top_cs_keywords", {})),
                "samples": _clean_samples(sample_response, label_sample_size),
            }
        )

    package = {
        "intent_type": "tertiary_top_cause_analysis",
        "doc_total": doc_total,
        "tertiary_total": tertiary_total,
        "top_n": top_n,
        "samples_per_label": requested_samples,
        "sample_strategy": {
            "mode": "dynamic_by_total",
            "basis_total": doc_total or tertiary_total,
            "max_payload_chars": MAX_EVIDENCE_PAYLOAD_CHARS,
        },
        "items": items,
    }
    _trim_package_samples(package)
    return package


def dynamic_samples_per_label(total: int, *, top_n: int = DEFAULT_TOP_N) -> int:
    """Scale evidence depth with the current query/table size."""
    try:
        total = int(total or 0)
    except (TypeError, ValueError):
        total = 0
    if total >= 30_000:
        return 80
    if total >= 20_000:
        return 64
    if total >= 10_000:
        return 48
    if total >= 5_000:
        return 36
    if total >= 2_000:
        return 24
    return 12


def _extract_messages(text: str, *, prefer_user_messages: bool) -> list[str]:
    parsed = None
    if any(marker in text for marker in RAW_DIALOG_MARKERS):
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None

    user_messages: list[str] = []
    other_messages: list[str] = []
    if parsed is not None:
        _collect_messages(parsed, user_messages, other_messages)

    if not user_messages and not other_messages:
        matches = re.findall(r'["“]消息内容["”]\s*[:：]\s*["“](.*?)["”]', text)
        other_messages = [_clean_message(match) for match in matches]

    selected = user_messages if prefer_user_messages and user_messages else user_messages + other_messages
    deduped: list[str] = []
    seen: set[str] = set()
    for message in selected:
        cleaned = _clean_message(message)
        if not cleaned or cleaned in seen:
            continue
        if any(marker in cleaned for marker in BOILERPLATE_MARKERS):
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped[:5]


def _collect_messages(payload: Any, user_messages: list[str], other_messages: list[str]) -> None:
    if isinstance(payload, list):
        for item in payload:
            _collect_messages(item, user_messages, other_messages)
        return
    if not isinstance(payload, dict):
        return
    message = payload.get("消息内容") or payload.get("message") or payload.get("content") or payload.get("工单内容")
    sender = str(payload.get("发送方") or payload.get("sender") or "")
    if not message:
        for value in payload.values():
            _collect_messages(value, user_messages, other_messages)
        return
    cleaned = _clean_message(message)
    if not cleaned:
        return
    if "用户" in sender or "客户" in sender:
        user_messages.append(cleaned)
    else:
        other_messages.append(cleaned)


def _clean_message(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[A-Za-z0-9]{18,}", "", text)
    text = re.sub(r"(?<!\d)\d{11,}(?!\d)", "", text)
    return text.strip(" ;；,，。")


def _terms(field: str, size: int) -> dict[str, Any]:
    return {"terms": {"field": field, "size": size, "exclude": EMPTY_EXCLUDE}}


def _bucket_list(agg: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"key": bucket.get("key"), "count": int(bucket.get("doc_count", 0) or 0)} for bucket in agg.get("buckets", [])]


def _clean_samples(response: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    samples = []
    for hit in response.get("hits", {}).get("hits", [])[:limit]:
        source = hit.get("_source", {})
        content = clean_evidence_text(source.get("content"), CONTENT_LIMIT, prefer_user_messages=True)
        cs_reply = clean_evidence_text(source.get("cs_reply"), CS_REPLY_LIMIT, prefer_user_messages=False)
        appeal = clean_evidence_text(source.get("customer_key_appeal"), STRUCTURED_LIMIT)
        customer_keywords = clean_evidence_text(source.get("customer_keywords"), STRUCTURED_LIMIT)
        cs_action = clean_evidence_text(source.get("cs_key_action"), STRUCTURED_LIMIT)
        cs_keywords = clean_evidence_text(source.get("cs_keywords"), STRUCTURED_LIMIT)
        samples.append(
            {
                "service_time": source.get("service_time"),
                "scene_service_type": source.get("scene_service_type"),
                "scene_emotion": source.get("scene_emotion"),
                "tertiary_labels": source.get("tertiary_labels"),
                "content": content,
                "content_excerpt": content,
                "cs_reply": cs_reply,
                "cs_reply_excerpt": cs_reply,
                "customer_key_appeal": appeal,
                "appeal": appeal,
                "customer_keywords": customer_keywords,
                "cs_key_action": cs_action,
                "cs_keywords": cs_keywords,
            }
        )
    return samples


def _and_filter(base_query: dict[str, Any], extra_filter: dict[str, Any]) -> dict[str, Any]:
    if not base_query or base_query == {"match_all": {}}:
        return extra_filter
    return {"bool": {"filter": [base_query, extra_filter]}}


def _total_hits(response: dict[str, Any]) -> int:
    total = response.get("hits", {}).get("total", 0)
    if isinstance(total, dict):
        return int(total.get("value") or 0)
    return int(total or 0)


def _trim_package_samples(package: dict[str, Any]) -> None:
    current_limit = int(package.get("samples_per_label") or 0)
    while current_limit > MIN_SAMPLES_PER_LABEL and len(json.dumps(package, ensure_ascii=False)) > MAX_EVIDENCE_PAYLOAD_CHARS:
        current_limit -= 1
        for item in package.get("items", []):
            item["samples"] = item.get("samples", [])[:current_limit]
        package["samples_per_label"] = current_limit
