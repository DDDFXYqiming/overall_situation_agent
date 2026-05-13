# Overall Situation Agent

A local Python tool for turning structured spreadsheet records into a summarized HTML/Markdown report.

The project is designed for private, local analysis workflows. It reads local spreadsheet files, stores normalized records in Elasticsearch, runs deterministic aggregations, enriches trend data with schedule context, samples evidence for high-frequency tertiary labels, and uses an OpenAI-compatible LLM endpoint for report narratives and interactive data questions.

## Features

- Import one spreadsheet file or a directory of spreadsheet files.
- Normalize common tabular inputs into an Elasticsearch index.
- Generate local HTML and Markdown reports through one deterministic aggregation and rendering flow.
- Run an interactive command-line chat mode with `/help`, `/context`, `/report`, normal LLM replies, and read-only Elasticsearch data queries.
- Serve synchronous and job/SSE HTTP APIs for import, report, run, and chat workflows.
- Keep generated outputs, logs, and local credentials outside version control.
- Filter and analyze unlabeled records (missing primary labels) separately with multi-dimensional clustering (emotion, province, CSP, operation, latent needs, appeals) and time-trend analysis, rendered as independent dashed-border cards in the report.

## Requirements

- Python 3.9+
- Local Elasticsearch instance
- OpenAI-compatible LLM API key for report narratives and interactive data questions

## Setup

```powershell
python -m pip install -r requirements.txt
```

Create a local `.env` file based on `.env.example`:

```ini
ES_URL=http://localhost:9200
ES_INDEX=tagged_feedback
ES_VERIFY_CERTS=false

LLM_API_KEY=
LLM_REPORT_ENABLED=true
```

Do not commit `.env`, generated outputs, logs, or private datasets.

## Usage

Import data:

```powershell
python -m overall_situation_agent.cli import --input "<spreadsheet-or-directory>" --recreate-index
```

Start interactive mode:

```powershell
python -m overall_situation_agent.cli chat --schedule-input "<schedule-file.xlsx>"
```

Generate a report:

```powershell
python -m overall_situation_agent.cli report
```

Run import and report generation together:

```powershell
python -m overall_situation_agent.cli run --input "<spreadsheet-or-directory>" --schedule-input "<schedule-file.xlsx>"
```

Start the local API server:

```powershell
python -m overall_situation_agent.cli serve --host 127.0.0.1 --port 8000
```

Primary API routes:

- `GET /health`
- `POST /api/import`, `POST /api/report`, `POST /api/run`, `POST /api/chat`
- `POST /api/jobs/import`, `POST /api/jobs/report`, `POST /api/jobs/run`, `POST /api/jobs/chat`
- `GET /api/jobs/{job_id}`, `GET /api/jobs/{job_id}/events`

Generated files are written to `outputs/` by default.

## Notes

- Report generation requires `LLM_REPORT_ENABLED=true` and an available `LLM_API_KEY` or `DEEPSEEK_API_KEY`.
- Statistics and counts come from Elasticsearch aggregations; the LLM only writes narrative analysis.
- `chat` is a custom local CLI orchestrator, not a LangChain agent.

## Repository Hygiene

The repository intentionally excludes local secrets, generated reports, logs, caches, and internal notes. Public documentation is kept generic so the code can be reviewed without exposing private data structures or usage context.
