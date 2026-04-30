from __future__ import annotations

import json
import logging
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    content: str
    raw: dict[str, Any] | None = None
    used_fallback: bool = False


class OpenAICompatibleClient:
    """Minimal OpenAI-compatible chat-completions client, tested for DeepSeek-style endpoints."""

    def __init__(self, settings: Settings):
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout_seconds
        self.max_retries = settings.llm_max_retries
        self.report_timeout = settings.llm_report_timeout_seconds
        self.report_max_retries = settings.llm_report_max_retries
        self.report_max_tokens = settings.llm_report_max_tokens
        self.report_enabled = settings.llm_report_enabled

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        timeout_seconds: int | float | None = None,
        max_retries: int | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if not self.enabled:
            return LLMResponse(content="", used_fallback=True)

        request_body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None and max_tokens > 0:
            request_body["max_tokens"] = max_tokens
        payload = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = self.timeout if timeout_seconds is None else timeout_seconds
        retries = self.max_retries if max_retries is None else max(0, max_retries)
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    raw = json.loads(response.read().decode("utf-8"))
                content = raw["choices"][0]["message"]["content"]
                logger.info("LLM call succeeded model=%s attempt=%s", self.model, attempt + 1)
                return LLMResponse(content=content, raw=raw, used_fallback=False)
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                socket.timeout,
                KeyError,
                json.JSONDecodeError,
            ) as exc:
                last_error = exc
                logger.warning("LLM call failed attempt=%s error=%s", attempt + 1, exc)
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))

        logger.error("LLM unavailable after retries: %s", last_error)
        return LLMResponse(content="", used_fallback=True)


def parse_json_object(text: str) -> dict[str, Any] | None:
    if not text.strip():
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).replace("JSON\n", "", 1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
