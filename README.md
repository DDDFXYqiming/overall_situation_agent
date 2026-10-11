简体中文 | [English](README.en.md)

# Overall Situation Agent · 全局态势分析智能体

**面向服务工单与多维业务记录的本地数据智能聚合、分析与态势研报智能体**。

`Overall Situation Agent` 是一个兼具全流程数据清洗、Elasticsearch 聚合计算与大模型叙事研报生成的本地智能分析系统。它支持将零散的 Excel/CSV 业务记录批量导入带有 IK 中文分词的 Elasticsearch 集群中，基于严格的 DSL 查询模板体系执行多维数据透视，并结合大语言模型在“数据绝对锚定”的前提下，自动生成结构化、专业级态势分析报告（HTML / Markdown），同时配备 Vue 3 交互式 Web 工作台与 CLI 终端分析模式。

---

## 核心特性与架构

```
[原始 Excel / CSV 表格] ──> [字段标准化与清洗] ──> [Elasticsearch + IK 中文分词]
                                                                  │
                                                                  ▼
[HTML / Markdown 态势报告] <── [LLM 深度洞察与叙事] <── [DSL 模板聚合运算 (es_templates)]
          ▲
          │
[Vue 3 Web 工作台 / 交互式 CLI / SSE 作业流]
```

* **双轨驱动（Mapping & Template-Driven）**：
  * **结构化索引映射（`es_mapping.json`）**：定义规范字段类型与 IK 细粒度分词策略，字段缺失或分词异常具备清晰报错机制。
  * **DSL 模板注册表（`es_templates/*.json`）**：将业务统计逻辑与自然语言查询意图解耦为声明式 JSON 模板，所有 DSL 执行均受只读权限与占位符强校验保护。
* **数据严谨性保证（Numbers Anchored to ES）**：报表中的所有统计数字、环比变化与占比分布严格源自 Elasticsearch 原生聚合，大模型仅负责叙事润色、异动归因与决策建议，杜绝大模型数字幻觉。
* **全功能多端交互模式**：
  * **现代化 Vue 3 Web 工作台**：一键拖拽导入表格、查看导入作业流、发起自然语言问数、在线预览图文研报；
  * **交互式 CLI 终端**：快速在控制台执行结构化聚合与态势问答；
  * **RESTful & SSE 实时任务 API**：支持异步作业排队与进度流式推送。
* **时序与上下文关联**：支持精准的时间切片筛选，并可灵活叠加重大活动或赛程节点等外部业务上下文。

---

## 环境依赖

* **Python**：3.9 或更高版本
* **Node.js**：20 或更高版本（用于运行 Vue 3 Web 工作台）
* **搜索引擎**：本地或远程 Elasticsearch（推荐 8.x / 9.x，需安装对应版本的 IK 中文分词插件）
* **大语言模型**：任意 OpenAI 兼容的 API Key（用于态势叙事与洞察生成）

---

## 快速开始

### 1. 安装后端依赖

```powershell
python -m pip install -r requirements.txt
```

### 2. 配置环境变量

从模板复制并编辑本地 `.env` 文件：

```ini
ES_URL=http://localhost:9200
ES_INDEX=tagged_feedback
ES_VERIFY_CERTS=false

LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_REPORT_ENABLED=true
```

### 3. 一键启动 Web 工作台

系统提供开箱即用的一键启动脚本（自动检查前端依赖与端口状态）：

```powershell
.\start-web.ps1
```
*(或在根目录执行 `python -m overall_situation_agent.cli serve` 启动后端 API，在 `vue_app` 目录执行 `npm run dev` 启动前端)*

### 4. 命令行交互模式

```powershell
# 批量导入表格数据
python -m overall_situation_agent.cli import-data --file ./data/service_records.xlsx

# 生成指定时间段态势报告
python -m overall_situation_agent.cli generate-report --start-date 2026-09-01 --end-date 2026-09-30 --format html

# 启动交互式问数终端
python -m overall_situation_agent.cli chat
```

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
