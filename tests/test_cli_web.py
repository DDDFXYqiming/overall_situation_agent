from __future__ import annotations

import unittest
from pathlib import Path

from overall_situation_agent import cli


class CliWebParserTests(unittest.TestCase):
    def test_web_command_accepts_cli_style_startup_arguments(self) -> None:
        parser = cli.build_parser()

        args = parser.parse_args(
            [
                "web",
                "--import-input",
                "data.xlsx",
                "--schedule-input",
                "schedule.xlsx",
                "--recreate-index",
                "--start-date",
                "2026-03-01",
                "--end-date",
                "2026-03-31",
                "--output",
                "report.html",
                "--host",
                "127.0.0.1",
                "--api-port",
                "8010",
                "--web-port",
                "5178",
            ]
        )

        self.assertEqual(args.command, "web")
        self.assertEqual(args.import_input, Path("data.xlsx"))
        self.assertEqual(args.schedule_input, Path("schedule.xlsx"))
        self.assertTrue(args.recreate_index)
        self.assertEqual(args.start_date, "2026-03-01")
        self.assertEqual(args.end_date, "2026-03-31")
        self.assertEqual(args.output, Path("report.html"))
        self.assertEqual(args.api_port, 8010)
        self.assertEqual(args.web_port, 5178)


if __name__ == "__main__":
    unittest.main()
