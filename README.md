# 整体情况分析 Agent

生成《视频业务产品体验问题诊断及用户需求洞察分析报告》中"一、整体情况"部分的本地 Python 工具。

数据流程：**Excel → 导入 Elasticsearch → 聚合查询 → 生成 HTML/Markdown 报告**

当前内容：
- `1.1 问题分布概览`（一/二/三级标签分布）
- `1.1` 深挖项（问题链路归因、运营举措与隐性诉求、会员类型聚类、典型案例）
- `1.2 投诉趋势与异动表现`（支持传入日历 Excel 标注活动日，默认突出峰值日/异动日/代表样例）

---

## 项目能力说明

这个 Agent 只负责生成报告中的 **“一、整体情况”**，不生成后续大章。它适合把已经打标的相关工单汇总成可汇报的整体诊断材料。

核心能力：
- **多 Excel 合并分析**：`--input` 可以传单个 Excel，也可以传目录；目录下 `.xlsx/.xlsm` 会按文件名排序批量导入，同一 ES 索引共同分析。
- **中文表头适配**：支持新增表头，如 `工单编号`、`工单投诉内容`、`一级标签集合`、`运营举措`、`隐性需求描述`、`涉及业务/会员类型_聚类`。
- **核心摘要先行**：报告顶部先展示 `核心摘要`，把核心问题链路、退费/升级风险、运营举措、会员类型、隐性需求、峰值日提前呈现。
- **问题分布与链路归因**：保留一级/二级/三级标签分布，同时补充问题链路归因、洞察维度、时段、省份、处理耗时。
- **运营与潜在需求分析**：把 `运营举措`、`隐性需求描述`、`隐性需求理由`、`会员类型聚类` 纳入聚合，辅助判断活动规则、权益兑现、订退流程是否引发投诉。
- **趋势与异动分析**：按日统计问题量、负向情绪占比、峰值日和异动日；长日表默认只展示重点日期，避免淹没结论。
- **典型案例呈现**：从高频三级问题和运营举措中抽取样例原声，用于解释“怎么导致用户误订购/退费/退订”。

## 适用业务场景

- **产品经理**：看哪个会员类型、内容权益或订退链路问题最多，定位产品规则、权益配置、观看体验问题。
- **业务运营**：看某个运营举措或活动是否带来投诉，判断活动告知、权益兑现、客服话术是否需要调整。
- **客服/服务治理**：看退费诉求、升级投诉倾向、处理耗时和典型案例，优先处理高风险问题。
- **汇报材料准备**：直接生成 HTML 和 Markdown，用于快速复盘整体情况或拆分查看 `1.1`/`1.2`。

## 报告输出结构

报告生成后会包含：
- `核心摘要`：放在最前面，先给本次整体结论。
- `1.1 问题分布概览`：一级/二级/三级标签分布、标签下钻、问题链路归因、运营举措与隐性诉求、会员类型聚类、典型案例。
- `1.2 投诉趋势与异动表现`：每日趋势图、峰值日、负向情绪占比、活动日样例、异动节点、重点日期明细。
- `口径说明`：说明数据来源、多标签统计、趋势窗口、活动日标注和当前未覆盖的终端/App 版本字段。

## 问答智能体能回答的问题

配置 LLM 后，`chat` 模式支持自然语言查询；未配置 LLM 时，也能处理部分确定性聚合问题。

示例：
- `哪个会员类型投诉最多`
- `隐性需求 top 是什么`
- `某活动相关投诉有哪些`
- `会员权益误订购怎么导致退费`
- `峰值日主要问题是什么`
- `退费诉求有多少条`

## 新增字段表格接入说明

新增目录中的两张表可以作为同一语料池合并分析。核心中文字段会映射到标准字段：

| 中文表头 | 标准字段 | 用途 |
|----------|----------|------|
| `工单编号` | `gd_identity` | ES `_id`，用于去重覆盖 |
| `工单投诉内容` / `工单内容` | `content` | 样例原声、全文查询 |
| `服务时间` | `service_time` | 趋势分析 |
| `省份名称` | `province_name` | 基础信息 |
| `时段` | `time_period` | 问题链路归因 |
| `服务时间到截止时间的耗时（分钟为单位）` | `duration_minutes` | 处理耗时 |
| `一级标签集合` | `primary_labels` | 一级问题分布 |
| `二级标签集合` | `secondary_labels` | 二级问题分布 |
| `三级标签集合` | `tertiary_labels` | 三级问题分布与典型案例 |
| `活动信息` | `match_info` / `match_label` | 活动/场次线索 |
| `运营举措` | `operation_action` | 运营举措聚合 |
| `隐性需求描述` | `latent_need` | 潜在需求分析 |
| `隐性需求理由` | `latent_need_reason` | 潜在需求解释 |
| `涉及业务/会员类型_聚类` | `biz_member_cluster` | 会员类型聚类 |

导入规则：
- 不带 `--recreate-index`：保留旧索引数据，新文件追加到同一索引共同分析。
- 带 `--recreate-index`：先清空并重建索引，再导入本次输入。
- 已存在的索引会自动补齐新增标准字段 mapping；如果历史上已把同名字段动态建成不兼容类型，建议使用 `--recreate-index` 清空后重导。
- 两表 `工单编号` 不重叠时会追加；若重叠，后导入记录覆盖前导入记录，避免重复计数。
- ES 可容纳不同原始字段名，但报告只统计映射后的标准字段；因此重点是标准字段一致，不要求 Excel 必须使用英文表头。

---

## 环境要求

- Python 3.9+
- Elasticsearch 本地可用（本机路径 `C:\tools\elasticsearch-9.3.3`）

---

## 快速开始

### 1. 安装依赖

```powershell
cd C:\Users\86187\Desktop\营服工作记录2026\调研\标签\overall_situation_agent
python -m pip install -r requirements.txt
```

### 2. 配置 `.env`

创建 `.env` 文件，最少配置：

```ini
ES_URL=http://localhost:9200
ES_INDEX=tagged_feedback
ES_VERIFY_CERTS=false
```

可选的大模型配置（DeepSeek，用于智能对话回复和 DSL 生成）：

```ini
LLM_API_KEY=your_api_key
# 或等效的：DEEPSEEK_API_KEY=your_api_key
# LLM_BASE_URL=https://api.deepseek.com    # 默认值，可选
# LLM_MODEL=deepseek-chat                   # 默认值，可选
```

### 3. 启动 Elasticsearch

```powershell
Start-Process -FilePath "C:\tools\elasticsearch-9.3.3\bin\elasticsearch.bat" `
  -WorkingDirectory "C:\tools\elasticsearch-9.3.3" -WindowStyle Minimized
```

验证：`Invoke-RestMethod -Uri "http://localhost:9200" -Method Get`

> ES 启动后数据持久化存储，重启 ES 不需要重新导入数据。

### 4. 导入数据

```powershell
# 导入完整数据（重建索引）
python -m overall_situation_agent.cli import --input "..\data\labeled_output.xlsx" --recreate-index

# 或小样本调试
python -m overall_situation_agent.cli import --input "..\data\tagged_output.xlsx" --recreate-index

# 导入目录下多张新增字段表（共同分析）
python -m overall_situation_agent.cli import --input "..\data\new_fields_batch" --recreate-index

# 追加导入新文件到同一索引（不清空旧数据）
python -m overall_situation_agent.cli import --input "..\data\new_batch.xlsx"
```

> 同一文件或同一目录清单不会重复导入（状态记录在 `logs/import_state.json`）。如果明确要清空重导，请加 `--recreate-index`。

### 5. 使用

```powershell
# 启动对话窗口（手动输入问题）
python -m overall_situation_agent.cli chat

# 启动对话窗口 + 导入数据（首次使用）
python -m overall_situation_agent.cli chat --import-input "..\data\labeled_output.xlsx"

# 导入 + 生成报告（一次完成）
python -m overall_situation_agent.cli run --input "..\data\tagged_output.xlsx"
```

---

## 命令详解

### `import` — 导入 Excel 到 ES

```powershell
python -m overall_situation_agent.cli import --input <Excel路径> [--recreate-index]
```

| 参数 | 说明 |
|------|------|
| `--input` | Excel 文件路径或目录路径（必需）；目录导入时跳过 `~$` 临时文件 |
| `--recreate-index` | 重建索引（覆盖已有数据） |

### `chat` — 对话窗口

```powershell
python -m overall_situation_agent.cli chat [--import-input <Excel路径>] [--schedule-input <日历Excel>]
```

- **普通输入**：不做数据查询则直接对话，不生成文档
- **数据问题**（如"业务体验有多少条"）：自动查 ES 并回答
- **`/report`**：生成完整报告（支持日期范围，如 `/report 2026-01-01 到 2026-01-31`）
- **`/help`**：查看帮助
- **`/context`**：查看会话状态

### `report` — 直接生成报告

```powershell
python -m overall_situation_agent.cli report [--start-date 2026-01-01] [--end-date 2026-01-31] [--schedule-input <日历Excel>]
```

### `run` — 导入 + 生成报告（一步完成）

```powershell
python -m overall_situation_agent.cli run --input <Excel路径或目录路径> [--start-date ...] [--end-date ...] [--schedule-input ...]
```

---

## 输出

报告统一输出到 `outputs/`，每次生成同步输出 `.html` 和 `.md`：

```
outputs/overall_situation_20260421_105333_整体情况报告.html
outputs/overall_situation_20260421_105333_整体情况报告.md
```

---

## Excel 输入格式

支持英文标准字段，也支持上文列出的中文表头映射。导入后报告统一统计标准字段。

必需字段：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `gd_identity` | 文本 | 工单唯一标识 | `GD20260101001` |
| `content` | 文本 | 用户反馈内容 | `播放卡顿严重` |

核心业务字段（标签字段支持 `、` `,` `；` 等分隔符多值）：

| 字段 | 说明 |
|------|------|
| `primary_labels` | 一级问题标签 |
| `secondary_labels` | 二级问题标签 |
| `tertiary_labels` | 三级问题标签 |
| `scene_emotion` | 情绪标签 |
| `service_time` | 服务时间（日期格式） |
| `province_name` | 省份名称 |

完整字段列表见 [schema.py](overall_situation_agent/schema.py)。

---

## 全部配置项（`.env`）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ES_URL` | `http://localhost:9200` | ES 地址 |
| `ES_INDEX` | `tagged_feedback` | ES 索引名 |
| `ES_USERNAME` | — | ES 用户名 |
| `ES_PASSWORD` | — | ES 密码 |
| `ES_VERIFY_CERTS` | `false` | 是否验证 SSL |
| `LLM_API_KEY` | — | DeepSeek API Key |
| `DEEPSEEK_API_KEY` | — | 等效于 LLM_API_KEY |
| `LLM_BASE_URL` | `https://api.deepseek.com` | LLM 接口地址 |
| `LLM_MODEL` | `deepseek-chat` | LLM 模型名 |
| `LLM_TIMEOUT_SECONDS` | `45` | LLM 请求超时 |
| `LLM_MAX_RETRIES` | `2` | LLM 重试次数 |
| `IMPORT_BATCH_SIZE` | `500` | 批量导入批次大小 |
| `OUTPUTS_DIR` | `outputs` | 报告输出目录 |
| `LOGS_DIR` | `logs` | 日志目录 |

---

## 日志

```powershell
Get-Content logs\agent.log -Tail 50
```

---

## 说明

- 未配置 LLM API Key 时，`/report` 仍可生成报告，文案退回规则生成；智能对话查询不可用
- 日历文件通过 `--schedule-input` 传入，用于 `1.2` 趋势图中标注活动日
- HTML 使用内联 SVG/CSS，不依赖外网 CDN
