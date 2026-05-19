from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from overall_situation_agent import cli


class CliChatStartupTests(unittest.TestCase):
    def test_chat_without_import_input_rejects_missing_index_before_interactive_loop(self) -> None:
        args = SimpleNamespace(
            command="chat",
            import_input=None,
            recreate_index=False,
            schedule_input=Path("schedule.xlsx"),
            project_dir=Path("."),
        )
        settings = SimpleNamespace(
            es_index="missing-chat-index",
            logs_dir=Path("logs"),
            outputs_dir=Path("outputs"),
        )

        class FakeIndices:
            def exists(self, index: str) -> bool:
                return False

        class FakeAgent:
            def __init__(self, settings):
                self.es = SimpleNamespace(indices=FakeIndices())

            def import_data(self, *args, **kwargs):  # pragma: no cover - should not be called
                raise AssertionError("import_data should not be called")

        class FakeInteractiveApp:
            def __init__(self, *args, **kwargs):  # pragma: no cover - should not be called
                raise AssertionError("interactive app should not start")

        with (
            patch.object(cli, "build_parser", return_value=SimpleNamespace(parse_args=lambda: args)),
            patch("overall_situation_agent.agent.OverallSituationAgent", FakeAgent),
            patch("overall_situation_agent.config.load_settings", return_value=settings),
            patch("overall_situation_agent.interactive_app.InteractiveOverallSituationApp", FakeInteractiveApp),
            patch("overall_situation_agent.logging_setup.setup_logging"),
        ):
            with self.assertRaises(SystemExit) as raised:
                cli.main()

        message = str(raised.exception)
        self.assertIn("Elasticsearch 索引不存在：missing-chat-index", message)
        self.assertIn("--import-input", message)
        self.assertIn("--recreate-index", message)


if __name__ == "__main__":
    unittest.main()
