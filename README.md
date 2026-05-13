# Overall Situation Agent

A full-featured local Python agent for turning spreadsheet records into a summarized HTML/Markdown report.

This edition keeps deterministic aggregation and report generation while adding interactive chat and local API/SSE server layers.

## Features

- Import one spreadsheet file or a directory of spreadsheet files.
- Normalize tabular records into an Elasticsearch index.
- Generate local HTML and Markdown reports from Elasticsearch aggregations.
- Apply OpenAI-compatible LLM narrative generation for report wording.
- Support date-range filtering and optional schedule-context annotation.
- Run an interactive command-line chat mode with read-only Elasticsearch data queries.
- Serve synchronous and job/SSE HTTP APIs for import, report, run, and chat workflows.

## Requirements

- Python 3.9+
- Local Elasticsearch instance
- OpenAI-compatible LLM API key

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

## Usage

Import data:

```powershell
python -m overall_situation_agent.cli import --input "<spreadsheet-or-directory>" --recreate-index
```

Generate a report:

```powershell
python -m overall_situation_agent.cli report
```

Run import and report generation together:

```powershell
python -m overall_situation_agent.cli run --input "<spreadsheet-or-directory>"
```

Run with date filters and schedule input:

```powershell
python -m overall_situation_agent.cli run --input "<spreadsheet-or-directory>" --start-date 2026-01-01 --end-date 2026-01-31 --schedule-input "<schedule-file.xlsx>"
```

Start interactive chat:

```powershell
python -m overall_situation_agent.cli chat --schedule-input "<schedule-file.xlsx>"
```

Start the local API server:

```powershell
python -m overall_situation_agent.cli serve --host 127.0.0.1 --port 8000
```

Generated files are written to `outputs/` by default.

## Configuration

Important environment variables:

- `ES_URL`, `ES_INDEX`, `ES_USERNAME`, `ES_PASSWORD`, `ES_VERIFY_CERTS`
- `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `DEEPSEEK_API_KEY`
- `LLM_REPORT_ENABLED`, `LLM_REPORT_TIMEOUT_SECONDS`, `LLM_REPORT_MAX_RETRIES`, `LLM_REPORT_MAX_TOKENS`
- `IMPORT_BATCH_SIZE`, `OUTPUTS_DIR`, `LOGS_DIR`, `IMPORT_STATE_FILE`

## API Routes

- `GET /health`
- `POST /api/import`, `POST /api/report`, `POST /api/run`, `POST /api/chat`
- `POST /api/jobs/import`, `POST /api/jobs/report`, `POST /api/jobs/run`, `POST /api/jobs/chat`
- `GET /api/jobs/{job_id}`, `GET /api/jobs/{job_id}/events`

## Differences From Simple Edition

- Added: interactive chat mode and query-builder conversation flow.
- Added: local API server dependencies and runtime path.
- Added: synchronous and job/SSE HTTP APIs.
- Kept: import pipeline, deterministic aggregations, schedule-context support, evidence sampling, report rendering, and LLM narrative generation.
- Available commands: `import`, `report`, `run`, `chat`, `serve`.

## Repository Hygiene

This public repository intentionally excludes secrets, local environment files, generated outputs, private datasets, and internal working notes.

Examples and descriptions are anonymized to avoid exposing sensitive business terms or source data context.
