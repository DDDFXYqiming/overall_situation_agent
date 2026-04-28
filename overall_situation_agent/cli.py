from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the 一、整体情况 section from tagged feedback data.")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd(), help="Directory containing optional .env file.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import one Excel file or a directory of Excel files into Elasticsearch.")
    import_parser.add_argument("--input", type=Path, required=True, help="Excel file or directory. Directory imports .xlsx/.xlsm files in sorted order and skips ~$ temporary files.")
    import_parser.add_argument("--recreate-index", action="store_true")

    report_parser = subparsers.add_parser("report", help="Generate HTML and Markdown reports from Elasticsearch aggregations.")
    report_parser.add_argument("--output", type=Path, help="Defaults to outputs/<timestamp>_report.html.")
    report_parser.add_argument("--start-date", type=str)
    report_parser.add_argument("--end-date", type=str)
    report_parser.add_argument("--schedule-input", type=Path, help="Optional league schedule Excel file for matchday markers.")

    run_parser = subparsers.add_parser("run", help="Import data, run aggregations, and generate HTML and Markdown reports.")
    run_parser.add_argument("--input", type=Path, required=True, help="Excel file or directory. Directory imports .xlsx/.xlsm files in sorted order and skips ~$ temporary files.")
    run_parser.add_argument("--output", type=Path, help="Defaults to outputs/<timestamp>_report.html.")
    run_parser.add_argument("--start-date", type=str)
    run_parser.add_argument("--end-date", type=str)
    run_parser.add_argument("--recreate-index", action="store_true")
    run_parser.add_argument("--schedule-input", type=Path, help="Optional league schedule Excel file for matchday markers.")

    chat_parser = subparsers.add_parser("chat", help="Start the continuous command-line agent.")
    chat_parser.add_argument("--import-input", type=Path, help="Optional Excel file or directory to import before entering chat.")
    chat_parser.add_argument("--recreate-index", action="store_true")
    chat_parser.add_argument("--schedule-input", type=Path, help="Optional league schedule Excel file for matchday markers.")

    return parser


def main() -> None:
    args = build_parser().parse_args()

    try:
        from .agent import OverallSituationAgent
        from .config import load_settings
        from .interactive_app import InteractiveOverallSituationApp
        from .logging_setup import setup_logging
        from .output_naming import normalize_report_path
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown"
        raise SystemExit(
            f"Missing dependency [{missing}]. Please run: python -m pip install -r requirements.txt"
        ) from exc

    settings = load_settings(args.project_dir)
    setup_logging(settings.logs_dir)
    agent = OverallSituationAgent(settings)

    if args.command == "import":
        result = agent.import_data(args.input, recreate_index=args.recreate_index)
        print(result.message)
        return

    if args.command == "report":
        output_path = normalize_report_path(settings.outputs_dir, args.output, "整体情况报告")
        output = agent.generate_report(
            output_path,
            start_date=args.start_date,
            end_date=args.end_date,
            schedule_input=args.schedule_input,
        )
        print(f"HTML report generated: {output.resolve()}")
        print(f"Markdown report generated: {output.with_suffix('.md').resolve()}")
        return

    if args.command == "run":
        output_path = normalize_report_path(settings.outputs_dir, args.output, "整体情况报告")
        output = agent.run(
            input_path=args.input,
            output_path=output_path,
            start_date=args.start_date,
            end_date=args.end_date,
            recreate_index=args.recreate_index,
            schedule_input=args.schedule_input,
        )
        print(f"HTML report generated: {output.resolve()}")
        print(f"Markdown report generated: {output.with_suffix('.md').resolve()}")
        return

    if args.command == "chat":
        if args.import_input:
            result = agent.import_data(args.import_input, recreate_index=args.recreate_index)
            print(result.message)
        InteractiveOverallSituationApp(settings, schedule_input=args.schedule_input).run()


if __name__ == "__main__":
    main()
