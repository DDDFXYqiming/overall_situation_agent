# Overall Situation Agent

A local Python tool for turning structured spreadsheet records into a summarized HTML/Markdown report.

The project is designed for private, local analysis workflows. It reads local spreadsheet files, stores normalized records in Elasticsearch, runs deterministic aggregations, and can optionally use an OpenAI-compatible LLM endpoint for natural-language interaction and report wording.

## Features

- Import one spreadsheet file or a directory of spreadsheet files.
- Normalize common tabular inputs into an Elasticsearch index.
- Generate a local HTML and Markdown report.
- Run an interactive command-line chat mode.
- Keep generated outputs, logs, and local credentials outside version control.

## Requirements

- Python 3.9+
- Local Elasticsearch instance
- Optional OpenAI-compatible LLM API key

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
```

Do not commit `.env`, generated outputs, logs, or private datasets.

## Usage

Import data:

```powershell
python -m overall_situation_agent.cli import --input "<spreadsheet-or-directory>" --recreate-index
```

Start interactive mode:

```powershell
python -m overall_situation_agent.cli chat
```

Generate a report:

```powershell
python -m overall_situation_agent.cli report
```

Run import and report generation together:

```powershell
python -m overall_situation_agent.cli run --input "<spreadsheet-or-directory>"
```

Generated files are written to `outputs/` by default.

## Repository Hygiene

The repository intentionally excludes local secrets, generated reports, logs, caches, and internal notes. Public documentation is kept generic so the code can be reviewed without exposing private data structures or usage context.
