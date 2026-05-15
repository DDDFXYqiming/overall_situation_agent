from __future__ import annotations

import unittest
from unittest.mock import patch

from overall_situation_agent.web_launcher import _npm_command


class WebLauncherTests(unittest.TestCase):
    def test_npm_command_prefers_windows_cmd_shim(self) -> None:
        def fake_which(name: str) -> str | None:
            return "C:/Program Files/nodejs/npm.cmd" if name == "npm.cmd" else "C:/Program Files/nodejs/npm"

        with patch("overall_situation_agent.web_launcher.shutil.which", side_effect=fake_which):
            self.assertEqual(_npm_command(), "C:/Program Files/nodejs/npm.cmd")

    def test_npm_command_reports_missing_node(self) -> None:
        with patch("overall_situation_agent.web_launcher.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "未找到 npm"):
                _npm_command()


if __name__ == "__main__":
    unittest.main()
