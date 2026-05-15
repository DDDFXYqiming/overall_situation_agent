# Overall Situation Agent 产品规格说明书

## 1. 产品定位

`overall_situation_agent` 是一个本地运行的 Python 分析工具，用于把已打标的 Excel 服务数据导入 Elasticsearch，并生成“整体情况”章节的 HTML 与 Markdown 报告。

当前产品以 `es_mapping.json` 和 `es_templates/*.json` 为核心配置：

- `es_mapping.json` 定义 Elasticsearch 索引 settings 与 mappings。
- `es_templates/*.json` 定义报告生成和自然语言查询所需的只读 ES 查询。
- CLI、API、chat、report、web 对外用法保持兼容。
- LLM 负责自然语言总结，不负责统计数字。

当前项目不是 LangChain agent，也没有 LangChain 风格的工具注册表。它由自研编排模块组成：

- CLI 命令：`import`、`report`、`run`、`chat`、`serve`、`web`
- 报告编排：`OverallSituationAgent`
- Mapping 加载：`mapping_loader`
- 模板注册与执行：`TemplateRegistry`、`TemplateExecutor`
- 交互式智能体：`InteractiveOverallSituationApp`
- 只读 ES 查询器：`ESQueryBuilder`
- OpenAI-compatible LLM 客户端：`OpenAICompatibleClient`
- 本地 FastAPI/SSE API：`overall_situation_agent.api`
- Vue 3 Web 工作台：`vue_app/`

## 2. 用户目标

核心用户希望完成三类任务：

1. 把一份 Excel 或一个目录中的多份 Excel 导入本地 ES 索引。
2. 基于已导入数据生成完整“整体情况”报告。
3. 在 CLI、HTTP API 或 Web 页面中追问数据问题，必要时通过 `/report` 生成报告。

## 3. 核心流程

报告生成链路：

```text
Excel -> 字段标准化 -> es_mapping.json 建索引 -> bulk 写入 ES
-> es_templates 运行时模板查询 -> 聚合结果标准化 -> 赛程合并
-> 三级标签证据抽样 -> LLM 叙事与数字锚点校验
-> HTML/Markdown 渲染 -> 报告校验
```

导入链路：

```text
输入路径 -> 收集 .xlsx/.xlsm -> 读取工作表 -> 表头别名映射
-> 行级标准化 -> schema.index_mapping 读取 es_mapping.json
-> ensure_index -> bulk 写入 ES -> import_state 记录
```

交互式智能体链路：

```text
用户输入 -> 内置命令路由
  -> /help 输出帮助
  -> /context 输出会话状态
  -> /report 调用报告生成链路
  -> 数据问题优先匹配 es_templates 并执行 ES 查询
  -> 模板未覆盖时使用安全 fallback DSL
  -> 普通问题调用 LLM 普通回复
```

API 链路：

```text
serve -> FastAPI app
  -> 同步接口：/api/import /api/report /api/run /api/chat
  -> 任务接口：/api/jobs/*
  -> SSE 事件：/api/jobs/{job_id}/events
```

Web 链路：

```text
web 命令/start_web.bat -> 启动 FastAPI + Vite -> 打开默认浏览器
  -> /api/web/startup 读取启动参数与非敏感配置
  -> 路径导入或 /api/uploads 上传 Excel 到 .uploads
  -> /api/jobs/import|report|run 执行任务
  -> /api/jobs/{job_id}/events 展示 SSE 进度
  -> /api/chat 复用交互式智能体
  -> /api/reports/{filename} 预览或下载 outputs 下报告
```

## 4. 功能范围

### 4.1 CLI

支持命令：

- `import`：导入 Excel 文件或目录到 ES。
- `report`：基于已有 ES 数据生成 HTML 和 Markdown 报告。
- `run`：先导入再生成报告。
- `chat`：启动交互式 CLI 智能体。
- `serve`：启动 FastAPI/SSE 本地 API 服务。
- `web`：启动 Vue Web 工作台、FastAPI API 服务和默认浏览器。

`web` 支持启动参数：

- `--import-input`
- `--schedule-input`
- `--recreate-index`
- `--start-date`
- `--end-date`
- `--output`
- `--host`
- `--api-port`
- `--web-port`

### 4.2 报告内容

报告输出包括：

- 核心摘要与发现
- `1.1 问题分布概览`
- 一级/二级/三级标签分布
- 一级标签下的用户核心诉求分布
- 三级问题分析小结
- 一级标签综合评价
- 典型问题深度分析
- `1.2 投诉趋势与异动表现`
- 每日趋势、赛事日原声、异动节点
- 未标注一二三级标签服务数据分析
- 方法说明

报告章节顺序、表格结构、统计口径和趋势节点必须与同一数据源下的基准报告保持一致。LLM 文字表达可不同，但不得改写数字含义。

### 4.3 交互式 chat

内置命令：

- `/help`
- `/context`
- `/report`
- `/exit`

普通输入分为：

- 数据问题：优先由 LLM 从模板库选择模板与参数，再执行安全只读 ES 查询。
- 模板未覆盖的数据问题：使用确定性 fallback 生成安全只读 ES DSL。
- 历史追问：基于 `AgentState` 返回会话历史。
- 非数据问题：通过 LLM 普通回复，不生成报告。

### 4.4 API

同步接口：

- `GET /health`
- `POST /api/import`
- `POST /api/report`
- `POST /api/run`
- `POST /api/chat`

任务/SSE 接口：

- `POST /api/jobs/import`
- `POST /api/jobs/report`
- `POST /api/jobs/run`
- `POST /api/jobs/chat`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/events`

任务状态保存在进程内存中，服务重启后不保留历史任务。

Web 增强接口：

- `POST /api/uploads`：上传一个或多个 `.xlsx/.xlsm` 文件，保存到 `.uploads/`，返回可被导入链路使用的本机路径。
- `GET /api/web/startup`：返回 web 启动参数、ES index、输出目录、上传目录、LLM 可用状态等非敏感配置。
- `GET /api/reports/{filename}`：只允许读取 `OUTPUTS_DIR` 下的 `.html` 或 `.md` 报告文件。

`/api/report`、`/api/run` 和 chat `/report` 的报告路径结果继续返回 `html_path`、`markdown_path`，并额外返回 `html_url`、`markdown_url` 供 Web 预览和下载。

### 4.5 Web

Web 端位于 `vue_app/`，使用 `Vite + Vue 3 + TypeScript + Pinia`。

页面结构：

- 左侧：模式导航、历史会话入口、快捷操作。
- 中间：ChatGPT 式对话区、输入框、报告卡片和报告预览。
- 右侧：数据导入、赛程输入、重建索引、日期范围、输出路径、服务配置、任务进度和 SSE 事件。

Web 功能覆盖 CLI 智能体能力：

- 路径导入和浏览器上传导入。
- 生成报告、导入并生成报告。
- 智能问答、`/help`、`/context`、`/report`。
- 查看任务状态与 SSE 事件。
- 预览 HTML 报告并下载 Markdown 报告。

启动方式：

- 一键启动：`.\start_web.bat`
- 命令行启动：`python -m overall_situation_agent.cli web`
- 启动时带导入参数：`python -m overall_situation_agent.cli web --import-input "<主数据>" --schedule-input "<赛程.xlsx>" --recreate-index`

默认端口从 API `8000`、Web `5173` 开始，若端口已占用，启动器选择后续可用端口。

## 5. 索引与模板规格

### 5.1 `es_mapping.json`

`es_mapping.json` 是 ES create-index body，必须可以直接用于建索引。

必需结构：

- `settings.number_of_shards`
- `settings.number_of_replicas`
- `settings.analysis`
- `mappings.dynamic`
- `mappings.properties`
- `mappings._meta.field_catalog`

文本字段必须使用项目 analyzer：

- `analyzer=migu_analyzer`
- `search_analyzer=migu_search_analyzer`

说明性字段目录放在 `mappings._meta.field_catalog`，不放入 `properties.<field>.meta`，避免 ES mapping 拒绝未知字段。

关键字段至少包括：

- `service_time`
- `primary_labels`
- `secondary_labels`
- `tertiary_labels`
- `scene_emotion`
- `scene_service_type`
- `customer_key_appeal`
- `biz_member_cluster`
- `match_label`

### 5.2 `es_templates/*.json`

模板文件顶层严格为：

```json
{
  "question": "...",
  "description": "...",
  "dsl": {}
}
```

模板分类：

- `00_common_*`：公共时间、已标注、未标注等基础查询。
- `01_distribution_*`：报告抬头、核心摘要、1.1 分布概览、未标注分析。
- `02_primary_*`：一级模块、三级标签分布、样本抽样、一级综合评价输入。
- `03_trend_*`：每日趋势、赛事日原声、异动节点。
- `90_runtime_*`：报告运行时模板，用于替代旧代码中的硬编码 ES DSL。

模板占位符包括但不限于：

- `{{start_date}}`
- `{{end_date_exclusive}}`
- `{{primary_label}}`
- `{{tertiary_label}}`
- `{{sample_size}}`

执行前必须经过统一安全校验。模板 DSL 顶层只能是合法 `_search` body 字段，禁止脚本、写入、runtime mapping 等能力。

## 6. 数据输入规格

输入可以是：

- 单个 `.xlsx` 或 `.xlsm`
- 包含多个 `.xlsx` / `.xlsm` 的目录

目录导入规则：

- 按文件名排序导入。
- 跳过 `~$` 开头的临时文件。
- 导入状态记录在 `logs/import_state.json`。

关键字段：

- `gd_identity`
- `content`
- `service_time`
- `end_time`
- `province_name`
- `primary_labels`
- `secondary_labels`
- `tertiary_labels`
- `scene_emotion`
- `scene_service_type`
- `customer_key_appeal`
- `cs_key_action`
- `operation_action`
- `latent_need`
- `biz_member_cluster`
- `match_info`
- `match_label`

中文表头会通过 `FIELD_ALIASES` 映射为内部标准字段。`FIELD_ALIASES` 用于导入清洗，不再作为 ES mapping 的唯一来源；索引结构以 `es_mapping.json` 为准。

## 7. ES 环境规格

本项目依赖 Elasticsearch IK 分词插件。

必须存在：

- `ik_max_word`
- `ik_smart`

如果 ES 未安装 IK 插件，建索引阶段必须失败并提示安装匹配版本的 `analysis-ik`，不得静默降级为 standard analyzer。

验证方式：

```powershell
curl http://localhost:9200/_cat/plugins?v
curl -X POST "http://localhost:9200/_analyze" -H "Content-Type: application/json" -d "{\"analyzer\":\"ik_smart\",\"text\":\"用户退订困难\"}"
```

## 8. 统计口径

项目同时维护两个总量：

- `total_with_unlabeled`：当前日期范围内全部服务数据量，包含未标注标签数据。
- `total`：已标注一级标签的数据量，用于主标签分布统计。

主报告口径：

- 标题、KPI、总体摘要优先展示 `total_with_unlabeled`。
- 一级/二级/三级标签分布基于已标注数据。
- 未标注数据通过独立分析块展示，不混入主标签分布。
- 日期结束条件为包含结束日期当天，内部转换为 `end_date_exclusive`。
- 多标签字段可重复计数，多个标签占比合计可能超过 100%。

## 9. LLM 使用规格

LLM 使用 OpenAI-compatible `/chat/completions` 接口。

报告生成要求：

- `LLM_REPORT_ENABLED=true`
- 已配置 `LLM_API_KEY` 或 `DEEPSEEK_API_KEY`
- 已成功抽取 `tertiary_evidence` 和 `tertiary_evidence_md`

LLM 负责生成：

- `executive_summary`
- `distribution_business_dimension`
- `primary_summaries`
- `typical_case_deep_dive`
- `tertiary_cause_detail`
- `primary_overall_evaluation`

数字保护要求：

- 统计数字必须来自 ES 聚合与代码计算。
- 提示词中传入关键数字锚点。
- 若 LLM 返回文本改错关键计数或占比，需要重试。
- 重试仍失败时使用确定性 fallback 文案。

## 10. 运行配置

`.env` 支持：

- `ES_URL`
- `ES_INDEX`
- `ES_USERNAME`
- `ES_PASSWORD`
- `ES_VERIFY_CERTS`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_API_KEY`
- `DEEPSEEK_API_KEY`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- `LLM_REPORT_ENABLED`
- `LLM_REPORT_TIMEOUT_SECONDS`
- `LLM_REPORT_MAX_RETRIES`
- `LLM_REPORT_MAX_TOKENS`
- `IMPORT_BATCH_SIZE`
- `OUTPUTS_DIR`
- `LOGS_DIR`
- `IMPORT_STATE_FILE`

## 11. 输出规格

默认输出目录：

```text
outputs/
```

报告文件：

```text
outputs/<timestamp>_整体情况报告.html
outputs/<timestamp>_整体情况报告.md
```

生成后的 HTML 必须通过 `validate_html_report_for_focus()` 校验。

## 12. 验收标准

基础验收命令：

```powershell
python -m compileall -q overall_situation_agent
python -m unittest discover -s tests
```

Mapping 与模板验收：

- `es_mapping.json` 能被 JSON 解析。
- `es_mapping.json` 顶层包含 `settings` 和 `mappings`。
- 关键字段存在且类型正确。
- 文本字段带 `migu_analyzer` / `migu_search_analyzer`。
- `es_templates/*.json` 能被 JSON 解析。
- 每个模板顶层严格为 `question`、`description`、`dsl`。
- 每个模板 DSL 通过只读 `_search` body 安全校验。

报告验收：

- `import` 能基于 `es_mapping.json` 建索引并写入 Excel 数据。
- `report` 和 `chat /report` 只能通过模板执行 ES 查询。
- Markdown 中总量、标签分布、趋势明细、赛事日、异动节点等数据与同一输入下的基准报告一致。
- 当前基准要求包括：总量 2,193、未标注 580、四个一级模块、19 个三级标签计数/占比、31 行每日明细、8 个赛事日、Top3 异动节点。
- LLM 自然语言允许表达差异，但不得改写统计数字。

API 验收：

- `python -m overall_situation_agent.cli serve --host 127.0.0.1 --port 8000` 能启动。
- `/health` 返回 `status=ok`。
- `/api/jobs/{job_id}/events` 能返回任务事件流。

Web 验收：

- `.\start_web.bat` 能启动 API、Vite，并使用系统默认浏览器打开页面。
- `python -m overall_situation_agent.cli web --import-input "<路径>" --schedule-input "<赛程.xlsx>" --recreate-index` 能打开页面并自动提交导入任务。
- 页面可完成上传导入、路径导入、报告生成、智能问答、`/report`、任务 SSE 查看、报告预览和 Markdown 下载。
- `cd vue_app && npm run typecheck && npm run build` 通过。
