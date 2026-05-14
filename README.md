# Overall Situation Agent

A local Python agent for importing tagged service records into Elasticsearch and generating the “overall situation” HTML/Markdown report.

The current workflow is mapping-driven and template-driven:

- `es_mapping.json` is the create-index body used by the importer.
- `es_templates/*.json` are the read-only Elasticsearch query templates used by report generation and natural-language data queries.
- The CLI, API, chat mode, report renderer, and LLM narrative layer all share the same Elasticsearch index and template registry.

## Features

- Import one spreadsheet file or a directory of spreadsheet files.
- Normalize spreadsheet columns into canonical Elasticsearch fields.
- Create the Elasticsearch index from `es_mapping.json`.
- Execute report and chat queries from JSON templates in `es_templates/`.
- Generate local HTML and Markdown reports from Elasticsearch aggregations.
- Add OpenAI-compatible LLM narrative wording while keeping report numbers anchored to ES results.
- Support date-range filtering and optional football schedule context.
- Run an interactive command-line chat mode with read-only Elasticsearch data queries.
- Serve synchronous and job/SSE HTTP APIs for import, report, run, and chat workflows.

## Requirements

- Python 3.9+
- Local Elasticsearch instance
- Elasticsearch IK analysis plugin matching the local ES version
- OpenAI-compatible LLM API key for report narrative generation

The bundled `es_mapping.json` uses `ik_max_word` and `ik_smart` analyzers for Chinese text fields. If IK is missing, index creation fails with a clear setup error instead of silently degrading the mapping.

## Setup

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install the matching IK plugin for the local Elasticsearch version. Example for Elasticsearch 9.3.3:

```powershell
C:\tools\elasticsearch-9.3.3\bin\elasticsearch-plugin.bat install --batch https://release.infinilabs.com/analysis-ik/stable/elasticsearch-analysis-ik-9.3.3.zip
```

Restart Elasticsearch after installation, then verify:

```powershell
curl http://localhost:9200/_cat/plugins?v
curl -X POST "http://localhost:9200/_analyze" -H "Content-Type: application/json" -d "{\"analyzer\":\"ik_smart\",\"text\":\"用户退订困难\"}"
```

Create a local `.env` file based on `.env.example`:

```ini
ES_URL=http://localhost:9200
ES_INDEX=tagged_feedback
ES_VERIFY_CERTS=false

LLM_API_KEY=
LLM_REPORT_ENABLED=true
```

## Mapping And Templates

`es_mapping.json` is loaded by `overall_situation_agent.mapping_loader` and returned by `schema.index_mapping()`. It contains:

- `settings.analysis` for the IK analyzers.
- `mappings.dynamic=true`.
- `mappings.properties` for runtime ES field types.
- `mappings._meta.field_catalog` for source-column descriptions and transformation notes.

`es_templates` contains flat JSON query templates with exactly these top-level keys:

```json
{
  "question": "...",
  "description": "...",
  "dsl": {}
}
```

Business-facing templates (`00_*`, `01_*`, `02_*`, `03_*`) support natural-language query matching. Runtime templates (`90_runtime_*`) externalize the report-generation Elasticsearch DSL that used to be hard-coded in Python.

All templates are loaded through `TemplateRegistry` and executed through `TemplateExecutor`. Template rendering supports placeholders such as `{{start_date}}`, `{{end_date_exclusive}}`, `{{primary_label}}`, `{{tertiary_label}}`, and `{{sample_size}}`; every rendered DSL body is validated as a read-only `_search` body before execution.

## Usage

Import data:

```powershell
python -m overall_situation_agent.cli import --input "<spreadsheet-or-directory>" --recreate-index
```

Generate a report from the existing ES index:

```powershell
python -m overall_situation_agent.cli report
```

Run import and report generation together:

```powershell
python -m overall_situation_agent.cli run --input "<spreadsheet-or-directory>"
```

Run with date filters and schedule input:

```powershell
python -m overall_situation_agent.cli run --input "<spreadsheet-or-directory>" --start-date 2026-03-01 --end-date 2026-03-31 --schedule-input "<schedule-file.xlsx>"
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

## Validation

Basic validation:

```powershell
python -m compileall -q overall_situation_agent
python -m unittest discover -s tests
```

The regression target for the current project is that a report generated from the same March 2026 source data keeps the same chapter order, tables, counts, percentages, daily rows, match-day rows, and anomaly rows as the baseline Markdown report. LLM text may vary, but anchored numbers are protected by deterministic ES aggregation and fallback wording.

## Repository Hygiene

The repository excludes secrets, local environment files, generated report outputs, private source spreadsheets, and temporary archives.

`es_mapping.json` and `es_templates/*.json` are committed because they are runtime configuration required by the current workflow.
