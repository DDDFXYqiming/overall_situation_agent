from __future__ import annotations

import argparse
from pathlib import Path


def _chat_missing_index_message(index_name: str, schedule_input: Path | None = None) -> str:
    schedule_arg = (
        f'  --schedule-input "{schedule_input.resolve()}" `\n'
        if schedule_input
        else '  --schedule-input "<赛事日 Excel 文件路径>" `\n'
    )
    return (
        f"Elasticsearch 索引不存在：{index_name}\n"
        "当前 chat 启动未提供 --import-input，程序不会自动猜测或导入数据源。\n"
        "首次测试请先显式导入主数据，例如：\n\n"
        "python -m overall_situation_agent.cli chat `\n"
        '  --import-input "<主数据 Excel 文件或目录路径>" `\n'
        f"{schedule_arg}"
        "  --recreate-index\n\n"
        "后续确认该索引已存在后，才可以只传 --schedule-input 直接进入对话。"
    )


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

    serve_parser = subparsers.add_parser("serve", help="Start the local FastAPI/SSE API server.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    web_parser = subparsers.add_parser("web", help="Start the Vue web app, API server, and default browser.")
    web_parser.add_argument("--import-input", type=Path, help="Optional Excel file or directory to import after the web app opens.")
    web_parser.add_argument("--schedule-input", type=Path, help="Optional league schedule Excel file for matchday markers.")
    web_parser.add_argument("--recreate-index", action="store_true")
    web_parser.add_argument("--start-date", type=str)
    web_parser.add_argument("--end-date", type=str)
    web_parser.add_argument("--output", type=Path, help="Optional report output filename.")
    web_parser.add_argument("--host", default="127.0.0.1")
    web_parser.add_argument("--api-port", type=int, default=8000)
    web_parser.add_argument("--web-port", type=int, default=5173)

    return parser


def main() -> None:
    args = build_parser().parse_args()

    try:
        from .agent import OverallSituationAgent
        from .config import load_settings
        from .interactive_app import InteractiveOverallSituationApp
        from .logging_setup import setup_logging
        from .output_naming import normalize_report_path
        from .web_launcher import launch_web
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown"
        raise SystemExit(
            f"Missing dependency [{missing}]. Please run: python -m pip install -r requirements.txt"
        ) from exc

    settings = load_settings(args.project_dir)
    setup_logging(settings.logs_dir)

    if args.command == "web":
        launch_web(
            settings=settings,
            project_dir=args.project_dir,
            host=args.host,
            api_port=args.api_port,
            web_port=args.web_port,
            import_input=args.import_input,
            schedule_input=args.schedule_input,
            recreate_index=args.recreate_index,
            start_date=args.start_date,
            end_date=args.end_date,
            output=args.output,
        )
        return

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
            if not result.success:
                raise SystemExit(1)
        elif not agent.es.indices.exists(index=settings.es_index):
            raise SystemExit(_chat_missing_index_message(settings.es_index, args.schedule_input))
        InteractiveOverallSituationApp(settings, schedule_input=args.schedule_input).run()
        return

    if args.command == "serve":
        try:
            import uvicorn

            from .api import create_app
        except ModuleNotFoundError as exc:
            missing = exc.name or "unknown"
            raise SystemExit(
                f"Missing dependency [{missing}]. Please run: python -m pip install -r requirements.txt"
            ) from exc
        uvicorn.run(create_app(settings), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
