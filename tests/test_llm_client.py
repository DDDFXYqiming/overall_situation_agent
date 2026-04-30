from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from overall_situation_agent.config import Settings
from overall_situation_agent.llm_client import OpenAICompatibleClient


class _FakeResponse:
    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")


class OpenAICompatibleClientTests(unittest.TestCase):
    def test_chat_allows_per_call_timeout_retry_and_token_overrides(self) -> None:
        settings = Settings(llm_api_key="test-key", llm_timeout_seconds=45, llm_max_retries=2)
        client = OpenAICompatibleClient(settings)
        captured_payloads = []

        def fake_urlopen(request, timeout):
            captured_payloads.append((json.loads(request.data.decode("utf-8")), timeout))
            return _FakeResponse()

        with patch("overall_situation_agent.llm_client.urllib.request.urlopen", side_effect=fake_urlopen) as urlopen:
            response = client.chat(
                [{"role": "user", "content": "hello"}],
                timeout_seconds=7,
                max_retries=0,
                max_tokens=123,
            )

        self.assertEqual(response.content, "ok")
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(captured_payloads[0][1], 7)
        self.assertEqual(captured_payloads[0][0]["max_tokens"], 123)


if __name__ == "__main__":
    unittest.main()
