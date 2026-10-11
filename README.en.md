[简体中文](README.md) | English

# Overall Situation Agent

**A local agent for spreadsheet ingestion, Elasticsearch aggregations, and LLM-assisted situation report generation.**

`Overall Situation Agent` is a comprehensive analytics platform combining spreadsheet data hygiene, multi-dimensional Elasticsearch aggregations, and LLM-driven narrative reporting. It transforms raw service and feedback spreadsheets into structured records in an IK-tokenized Elasticsearch cluster, runs template-driven queries across operational dimensions, and synthesizes publication-ready situation reports (HTML/Markdown) where statistical metrics remain strictly grounded in database aggregations.

---

## Architectural Highlights

```
[Raw Excel / CSV Tables] ──> [Schema Mapping & Cleaning] ──> [Elasticsearch + IK Analyzers]
                                                                     │
                                                                     ▼
[HTML / Markdown Reports] <── [Narrative Insight Engine] <── [DSL Query Templates (es_templates)]
           ▲
           │
[Vue 3 Web Workspace / Interactive CLI / SSE Job Stream]
```

* **Mapping & Template-Driven Design**:
  * **Explicit Index Mapping (`es_mapping.json`)**: Configures fine-grained field types alongside IK Chinese tokenization with zero silent schema degradations.
  * **DSL Template Registry (`es_templates/*.json`)**: Decouples analytical logic into modular JSON templates; runtime executions enforce read-only `_search` payloads and secure placeholder injections.
* **Grounded Statistical Integrity**: All numerical totals, ratios, and distributions are computed directly by Elasticsearch. The LLM focuses strictly on contextual narration, trend attribution, and executive summaries—eliminating hallucinated metrics.
* **Multi-Modal Operation**:
  * **Vue 3 Web Workspace**: Uploads spreadsheets via drag-and-drop, tracks background ingestion jobs, queries data in natural language, and previews interactive reports.
  * **Interactive CLI Shell**: Directly executes ad-hoc analytical queries and conversational drill-downs from the terminal.
  * **RESTful & SSE APIs**: Offers job queues and real-time streaming updates for automated pipelines.
* **Context & Temporal Filters**: Supports precise date-range slicing alongside external contextual overlays such as campaign windows or operational milestones.

---

## Requirements

* **Python**: 3.9 or newer
* **Node.js**: 20 or newer (for the Vue 3 workspace)
* **Elasticsearch**: Local or remote instance with matching Analysis IK plugin installed
* **Foundation Model**: Any OpenAI-compatible endpoint key for narrative synthesis

---

## Quick Start

### 1. Install Backend Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and adjust your cluster and model credentials:

```ini
ES_URL=http://localhost:9200
ES_INDEX=tagged_feedback
ES_VERIFY_CERTS=false

LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_REPORT_ENABLED=true
```

### 3. Launch Web Workspace

Start both API services and web frontend with the one-click launcher:

```powershell
.\start-web.ps1
```
*(Or launch backend with `python -m overall_situation_agent.cli serve` and frontend with `npm run dev` inside `vue_app`)*

### 4. CLI Execution

```powershell
# Import spreadsheets
python -m overall_situation_agent.cli import-data --file ./data/service_records.xlsx

# Compile situation report
python -m overall_situation_agent.cli generate-report --start-date 2026-09-01 --end-date 2026-09-30 --format html

# Interactive analytical terminal
python -m overall_situation_agent.cli chat
```

---

## License

This project is open-sourced under the [MIT License](LICENSE).
