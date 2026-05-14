from __future__ import annotations

import copy
import calendar
import json
import logging
import re
from typing import Any

from .es_client import ElasticsearchError, SimpleElasticsearch
from .evidence import EVIDENCE_SOURCE_FIELDS, MAX_EVIDENCE_PAYLOAD_CHARS, build_tertiary_evidence_package
from .llm_client import OpenAICompatibleClient, parse_json_object
from .mapping_loader import allowed_search_fields
from .taxonomy import CANONICAL_PRIMARY_TERTIARY, canonical_tertiary_label, tertiary_label_variants
from .template_executor import TemplateExecutor
from .template_registry import TemplateError, default_date_params

logger = logging.getLogger(__name__)


class ESQueryError(RuntimeError):
    pass


class LLMUnavailableError(ESQueryError):
    pass


class InvalidQueryError(ESQueryError):
    pass


ALLOWED_FIELDS = {
    "service_time",
    "end_time",
    "duration_minutes",
    "time_period",
    "label_group",
    "primary_labels",
    "secondary_labels",
    "tertiary_labels",
    "scene_emotion",
    "scene_service_type",
    "scene_event",
    "customer_key_appeal",
    "customer_key_appeal.keyword",
    "content",
    "content.keyword",
    "cs_reply",
    "cs_reply.keyword",
    "complaint_content",
    "complaint_content.keyword",
    "province_name",
    "province",
    "gd_identity",
    "source_file",
    "has_refund_demand",
    "has_escalation",
    "insight_dimension",
    "customer_keywords",
    "cs_keywords",
    "cs_key_action",
    "cs_key_action.keyword",
    "operation_action",
    "latent_need",
    "latent_need.keyword",
    "latent_need_reason",
    "latent_need_reason.keyword",
    "match_info",
    "match_info.keyword",
    "match_label",
    "biz_member_cluster",
    "biz_type",
    "marketing_activity_page",
    "marketing_activity_match_status",
    "marketing_activity_match_keywords",
    "age",
    "gender",
}

DEFAULT_SOURCE_FIELDS = [
    "service_time",
    "province_name",
    "primary_labels",
    "secondary_labels",
    "tertiary_labels",
    "scene_emotion",
    "scene_service_type",
    "scene_event",
    "customer_key_appeal",
    "customer_keywords",
    "content",
    "cs_reply",
    "operation_action",
    "cs_key_action",
    "cs_keywords",
    "latent_need",
    "latent_need_reason",
    "biz_member_cluster",
    "marketing_activity_page",
    "marketing_activity_match_status",
    "marketing_activity_match_keywords",
    "age",
    "gender",
    "match_info",
    "match_label",
    "time_period",
    "duration_minutes",
    "has_refund_demand",
    "has_escalation",
]

TOP_LEVEL_KEYS = {"query", "aggs", "aggregations", "size", "sort", "_source", "track_total_hits", "from", "timeout"}
BANNED_KEYS = {
    "script",
    "script_fields",
    "runtime_mappings",
    "suggest",
    "profile",
    "rescore",
    "pit",
    "search_after",
    "collapse",
    "delete",
    "update",
    "bulk",
    "indices",
    "query_string",
    "simple_query_string",
}
FIELD_CLAUSES = {"match", "match_phrase", "term", "terms", "range", "wildcard", "prefix"}
DATE_KEY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")
KEYWORD_FIELD_REWRITES = {
    "customer_key_appeal": "customer_key_appeal.keyword",
    "content": "content.keyword",
    "complaint_content": "complaint_content.keyword",
    "latent_need": "latent_need.keyword",
    "latent_need_reason": "latent_need_reason.keyword",
    "match_info": "match_info.keyword",
    "cs_key_action": "cs_key_action.keyword",
}
DISTRIBUTION_SPECS = [
    {
        "markers": ("三级", "三类"),
        "field": "tertiary_labels",
        "agg_name": "tertiary_distribution",
        "label": "三级标签",
    },
    {
        "markers": ("二级", "二类"),
        "field": "secondary_labels",
        "agg_name": "secondary_distribution",
        "label": "二级标签",
    },
    {
        "markers": ("一级", "一类"),
        "field": "primary_labels",
        "agg_name": "primary_distribution",
        "label": "一级标签",
    },
    {
        "markers": ("情绪",),
        "field": "scene_emotion",
        "agg_name": "emotion_distribution",
        "label": "情绪",
    },
    {
        "markers": ("省份", "地区", "地域"),
        "field": "province_name",
        "agg_name": "province_distribution",
        "label": "省份",
    },
    {
        "markers": ("运营举措", "运营措施", "活动", "举措"),
        "field": "operation_action",
        "agg_name": "operation_action_distribution",
        "label": "运营举措",
    },
    {
        "markers": ("会员类型", "业务类型", "会员", "聚类"),
        "field": "biz_member_cluster",
        "agg_name": "member_cluster_distribution",
        "label": "会员类型聚类",
    },
    {
        "markers": ("隐性需求", "潜在需求", "隐形诉求", "隐性诉求"),
        "field": "latent_need.keyword",
        "agg_name": "latent_need_distribution",
        "label": "隐性需求",
    },
    {
        "markers": ("时段", "时间段"),
        "field": "time_period",
        "agg_name": "time_period_distribution",
        "label": "时段",
    },
    {
        "markers": ("比赛", "赛事", "场次"),
        "field": "match_label",
        "agg_name": "match_distribution",
        "label": "比赛信息",
    },
]
DISTRIBUTION_TERMS = ("分布", "占比", "多少", "数量", "有哪些", "排行", "排名", "最多", "最高", "哪个", "什么", "top", "TOP")
TREND_TERMS = ("趋势", "峰值", "异动", "按天", "date_histogram", "聚合验证", "完整聚合")
FOLLOWUP_TERMS = ("刚才", "上一个", "上一条", "你说的", "按照你说的", "继续", "验证", "这个", "那个", "该")
DETAIL_TERMS = ("有哪些", "明细", "样例", "案例", "相关投诉", "相关工单", "怎么导致", "为什么")
TOP_TERMS = ("top", "TOP", "前五", "前5", "五个", "5个", "最多", "排名", "排行", "高频")
CAUSE_TERMS = ("为什么", "原因", "归因", "短板", "问题", "诉求", "客服", "处理", "分析")
KNOWN_OPERATIONS = (
    "会员促销活动",
    "高阶赛事数据展示",
    "好礼兑换",
    "智能解说",
    "社区化生态",
)
KNOWN_MEMBER_CLUSTERS = (
    "内容权益包系列",
    "专项会员系列",
    "高阶会员系列",
    "咪视界系列",
    "通看券系列",
    "单场赛事/单场解锁",
    "活动权益/票务",
)
KNOWN_INSIGHT_DIMENSIONS = ("用得亏", "用得难", "用得烦", "不适用")
KNOWN_TIME_PERIODS = ("凌晨", "上午", "中午", "下午", "晚上", "夜间")
KNOWN_PRIMARY_LABELS = tuple(CANONICAL_PRIMARY_TERTIARY.keys())
KNOWN_TERTIARY_LABELS = tuple(
    dict.fromkeys(label for labels in CANONICAL_PRIMARY_TERTIARY.values() for label in labels)
)


SYSTEM_PROMPT = """
你是 Elasticsearch 查询生成专家。根据用户问题，生成当前索引的只读 _search 查询 DSL。

可用字段：
- service_time: 服务时间（日期）
- primary_labels: 一级问题标签
- secondary_labels: 二级问题标签
- tertiary_labels: 三级问题标签
- scene_emotion: 情绪标签
- scene_service_type: 服务类型
- scene_event: 事件类型
- customer_key_appeal: 用户核心诉求
- customer_key_appeal.keyword: 用户核心诉求精确聚合字段
- customer_keywords: 用户诉求关键词
- cs_key_action: 客服关键处理动作
- cs_key_action.keyword: 客服关键处理动作精确聚合字段
- cs_keywords: 客服处理关键词
- content: 反馈内容
- content.keyword: 反馈内容精确聚合字段
- cs_reply: 处理意见/客服回复
- province_name: 省份
- has_refund_demand: 是否有退费诉求
- has_escalation: 是否有升级投诉倾向
- insight_dimension: 洞察维度，如用得亏、用得难、用得烦
- operation_action: 运营举措/活动
- latent_need: 隐性需求描述
- latent_need.keyword: 隐性需求精确聚合字段
- latent_need_reason: 隐性需求理由
- match_info: 比赛信息原始文本
- match_label: 比赛信息解析后的场次标签
- biz_member_cluster: 涉及业务/会员类型聚类
- label_group: 标签组
- marketing_activity_page: 营销活动页面名称
- marketing_activity_match_status: 营销活动匹配状态
- marketing_activity_match_keywords: 营销活动匹配关键词
- age: 年龄
- gender: 性别
- duration_minutes: 服务时间到截止时间的耗时，单位分钟
- time_period: 时段

只输出 JSON，结构必须为：
{
  "query": {完整 Elasticsearch search body},
  "explanation": "查询说明",
  "expected_fields": ["期望返回或分析的字段"]
}

约束：
1. query 只能是 _search body，不要输出 index、url、method。
2. 禁止 delete、update、bulk、script、runtime_mappings 等写入或脚本能力。
3. 明细查询 size 不超过 100；聚合查询可使用 size: 0。
4. 若用户没有明确日期，不要臆造日期范围。
5. 用户询问“某类/某标签有多少条”时，必须优先生成 term/terms 过滤，而不是 match_all。
6. 标签字段优先级：primary_labels（一级）→ secondary_labels（二级）→ tertiary_labels（三级）。
7. 常见一级标签示例：业务体验、内容体验、营销活动、使用体验。
8. 常见二级标签示例：权益使用、订购流程、计费争议、内容丰富度、奖品发放、内容质量、性能表现。
9. 常见三级标签示例：退订困难自动续费争议、权益无法兑换、无法订购扣费失败、权益价值感低、赛事覆盖率低、不知情订购、重复扣费。
10. 当用户追问“刚才/上一个/你说的/那个/最高的/继续验证”等内容时，必须结合对话上下文和最近一次查询结果补全对象。
11. 趋势、峰值、异动、date_histogram 类问题必须使用 service_time 的 date_histogram，并在每个日期桶下聚合 primary_labels、secondary_labels、tertiary_labels，便于判断峰值日主要问题。
12. 对 customer_key_appeal、content 做 terms 聚合或排序时，必须使用 customer_key_appeal.keyword、content.keyword。
13. 运营举措、会员类型、隐性需求、比赛信息类问题优先使用 operation_action、biz_member_cluster、latent_need.keyword、match_label。
14. 营销活动页面、营销活动匹配状态、营销活动关键词、年龄、性别类问题优先使用 marketing_activity_page、marketing_activity_match_status、marketing_activity_match_keywords、age、gender。
15. 只输出 JSON，不要输出 Markdown 或解释性正文。
""".strip()


ANALYSIS_PROMPT = """
你是数据分析专家。根据以下 Elasticsearch 查询结果，用自然语言回答用户问题。

要求：
1. 用简洁中文回答。
2. 引用查询结果中的具体数字、日期、标签或样例。
3. 只基于给定结果，不要编造数据。
4. 如果结果为空，明确说明未找到匹配数据，并建议用户换个范围或关键词。
5. 系统已经执行了 Elasticsearch 查询，payload.executed 为 true 时，不得说"无法直接执行 Elasticsearch 查询"、不得要求用户或运维再执行 DSL。
6. 峰值日、占比、TOP 标签等关键数字优先使用 result_summary，不要把 hits 样本当作全量统计。
7. 即使历史中已经回答过相似问题，也必须基于当前 payload 重新给出本次查询的关键数字和结论；不要只说"已展示""如需进一步分析"。
8. 如果用户问题明显不是数据查询问题（如询问对话历史、闲聊、问你是谁），请直接指出该问题不属于数据查询，并建议用户重新提问。不要强行生成数据回答。
9. 当 intent_metadata.intent_type 为 tertiary_top_cause_analysis，必须按固定结构回答：先列 TOP5 三级标签排序（数量+占比），再逐个解释为什么高频，最后总结共性产品/服务短板。
10. 做三级标签原因分析时，要结合 evidence_package.items 下每个标签的 content、cs_reply、customer_key_appeal、customer_keywords、cs_key_action、cs_keywords；不要把 ES 聚合本身说成“原因”，ES 只提供证据。
    对每个 TOP5 三级标签必须分成三组写：
    - 工单内容与客服回复：总结工单内容反复出现的问题场景，以及客服回复主要如何解释、核查、退费、记录或转派；
    - 客户关键诉求与客户诉求关键词：总结 customer_key_appeal 与 customer_keywords 反映的真实诉求，不要只罗列关键词；
    - 客服关键处理动作与客服处理关键词：总结 cs_key_action 与 cs_keywords 体现的处理路径，并说明这种处理方式为什么会让该类问题持续高频。
    每个三级标签不少于 3 个要点，每个要点 1-2 句，整体分析不能过短。
11. 禁止粘贴原始 JSON、整段对话、客服原文或用户原句；即便是短句也不要用引号复述原文，只能把样例中的用户表述和客服处理动作提炼成自然语言原因，例如“用户集中要求退订并退款，但客服侧多为解释规则、提交核查或引导等待，导致同类投诉反复出现”。
""".strip()


class ESQueryBuilder:
    """Generate, validate, execute, and summarize read-only Elasticsearch queries."""

    def __init__(self, es: SimpleElasticsearch, index_name: str, llm: OpenAICompatibleClient, max_size: int = 100):
        self.es = es
        self.index_name = index_name
        self.llm = llm
        self.max_size = max_size
        self.template_executor = TemplateExecutor()
        self.allowed_fields = allowed_search_fields() | ALLOWED_FIELDS

    def generate_intent(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        last_query_summary: dict[str, Any] | None = None,
        last_query_dsl: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        deterministic_intent = self.build_deterministic_intent(
            question,
            last_query_summary=last_query_summary,
            last_query_dsl=last_query_dsl,
        )
        if deterministic_intent:
            return deterministic_intent

        if not self.llm.enabled:
            raise LLMUnavailableError("当前无法使用智能数据查询，请配置 LLM_API_KEY/DEEPSEEK_API_KEY 后重试。")

        compact_history = (history or [])[-6:]
        template_intent = self._llm_template_intent(question, compact_history)
        if template_intent:
            return template_intent

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *compact_history,
            {"role": "user", "content": question},
        ]
        last_error: Exception | None = None
        for attempt in range(2):
            response = self.llm.chat(messages, temperature=0.0)
            if response.used_fallback or not response.content.strip():
                raise LLMUnavailableError("当前无法使用智能数据查询，请稍后重试。")

            parsed = parse_json_object(response.content)
            if not parsed:
                last_error = InvalidQueryError("模型输出不是合法 JSON。")
            else:
                try:
                    parsed["query"] = self.build_query(parsed)
                    parsed["expected_fields"] = self._sanitize_expected_fields(parsed.get("expected_fields"))
                    parsed["explanation"] = str(parsed.get("explanation") or "已生成只读 Elasticsearch 查询。")
                    return parsed
                except InvalidQueryError as exc:
                    last_error = exc

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"用户问题：{question}\n"
                        f"上一次输出无法执行，错误：{last_error}\n"
                        "请重新只输出符合约束的 JSON。"
                    ),
                },
            ]

        raise InvalidQueryError(f"无法生成安全可执行的查询 DSL：{last_error}")

    def build_deterministic_intent(
        self,
        question: str,
        last_query_summary: dict[str, Any] | None = None,
        last_query_dsl: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        q = question.strip()
        contextual = self._build_contextual_followup_intent(q, last_query_summary)
        if contextual:
            return self._finalize_intent(contextual)

        if self._is_tertiary_top_cause_question(q):
            return self._finalize_intent(self._tertiary_top_cause_intent(q))

        template_intent = self._template_intent(q)
        if template_intent:
            return template_intent

        if any(term in q for term in TREND_TERMS):
            return self._finalize_intent(self._trend_intent(q, last_query_dsl=last_query_dsl))

        filters = self._question_filters(q)
        if filters and any(term in q for term in DETAIL_TERMS):
            return self._finalize_intent(self._detail_intent(q, filters))

        for spec in DISTRIBUTION_SPECS:
            if any(marker in q for marker in spec["markers"]) and any(term in q for term in DISTRIBUTION_TERMS):
                return self._finalize_intent(self._distribution_intent(q, spec))

        return None

    def _template_intent(self, question: str) -> dict[str, Any] | None:
        params = self._template_params_from_question(question)
        template_id = self._select_template_id(question, params)
        if not template_id:
            return None
        return self._intent_from_template(template_id, params)

    def _llm_template_intent(self, question: str, history: list[dict[str, str]]) -> dict[str, Any] | None:
        templates = self.template_executor.registry.list_for_llm(limit=32)
        if not templates:
            return None
        prompt = {
            "user_question": question,
            "available_templates": templates,
            "output_schema": {
                "template_id": "one available template_id or null",
                "params": "object with any extracted start_date/end_date/primary_label/tertiary_label/sample_size",
                "explanation": "short Chinese explanation",
                "expected_fields": ["field names"],
            },
        }
        response = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是 ES 查询模板选择器。只能从 available_templates 选择 template_id，"
                        "不要直接生成 Elasticsearch DSL。无法匹配时输出 {\"template_id\": null}。"
                    ),
                },
                *history,
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            temperature=0.0,
        )
        if response.used_fallback or not response.content.strip():
            return None
        parsed = parse_json_object(response.content)
        if not parsed or not parsed.get("template_id"):
            return None
        params = self._template_params_from_question(question)
        model_params = parsed.get("params")
        if isinstance(model_params, dict):
            params.update({str(key): value for key, value in model_params.items() if value not in (None, "")})
        intent = self._intent_from_template(str(parsed.get("template_id")), params)
        if not intent:
            return None
        if parsed.get("explanation"):
            intent["explanation"] = str(parsed["explanation"])
        intent["expected_fields"] = self._sanitize_expected_fields(parsed.get("expected_fields")) or intent.get("expected_fields", [])
        return intent

    def _intent_from_template(self, template_id: str, params: dict[str, Any]) -> dict[str, Any] | None:
        try:
            body = self.template_executor.render(template_id, params)
            query = self.build_query({"query": body})
            template = self.template_executor.registry.get(template_id)
        except (TemplateError, RuntimeError, InvalidQueryError):
            return None
        expected_fields = self._fields_from_dsl(query)
        return {
            "query": query,
            "explanation": f"使用 ES 模板 [{template_id}]：{template.description}",
            "expected_fields": expected_fields,
            "metadata": {
                "intent_type": "template_query",
                "template_id": template_id,
                "template_params": params,
            },
        }

    def _template_params_from_question(self, question: str) -> dict[str, Any]:
        params = default_date_params(None, None)
        dates = self._extract_dates(question)
        if len(dates) >= 2:
            params.update(default_date_params(dates[0], dates[1]))
        elif len(dates) == 1:
            params.update(default_date_params(dates[0], dates[0]))
        else:
            month_range = self._extract_month_range(question)
            if month_range:
                params.update(default_date_params(month_range[0], month_range[1]))

        primary = self._extract_primary_label(question)
        tertiary = self._extract_tertiary_label(question)
        if primary:
            params["primary_label"] = primary
        if tertiary:
            params["tertiary_label"] = tertiary
        if "sample_size" not in params:
            params["sample_size"] = 24
        return params

    def _select_template_id(self, question: str, params: dict[str, Any]) -> str | None:
        if "未标注" in question:
            return "01_distribution_unlabeled_analysis"
        if any(term in question for term in ("数据周期", "时间范围", "日期范围")):
            return "01_distribution_header_period_range"
        if any(term in question for term in ("总服务", "总量", "服务数据量")):
            return "01_distribution_header_total_service_count"
        if any(term in question for term in TREND_TERMS):
            if "异动" in question:
                return "03_trend_anomaly_nodes"
            if "赛事日" in question and any(term in question for term in ("原声", "样例", "样本")):
                return "03_trend_matchday_voice_samples"
            if "每日明细" in question or "每天" in question:
                return "03_trend_daily_detail_table"
            return "03_trend_daily_aggregation"
        if params.get("primary_label") and params.get("tertiary_label") and any(term in question for term in ("占", "比例", "数量", "多少")):
            return "02_primary_tertiary_title_count"
        if params.get("primary_label") and "三级" in question:
            return "02_primary_tertiary_distribution_by_primary"
        if any(label in question for label in CANONICAL_PRIMARY_TERTIARY) and any(term in question for term in ("一级模块", "标题", "数量", "占比")):
            return "02_primary_module_title_counts"
        if any(term in question for term in ("核心摘要", "行动建议")):
            return "01_distribution_executive_summary_inputs"
        if any(marker in question for marker in ("一级", "二级", "三级", "情绪", "分布", "占比")):
            return "01_distribution_conclusion_aggregations"
        return None

    def _extract_dates(self, question: str) -> list[str]:
        matches = re.findall(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", question)
        return [f"{int(year):04d}-{int(month):02d}-{int(day):02d}" for year, month, day in matches]

    def _extract_month_range(self, question: str) -> tuple[str, str] | None:
        match = re.search(r"(20\d{2})年\s*(\d{1,2})月", question)
        if not match:
            match = re.search(r"(20\d{2})[-/.](\d{1,2})(?![-/.]\d)", question)
        if not match:
            return None
        year = int(match.group(1))
        month = int(match.group(2))
        last_day = calendar.monthrange(year, month)[1]
        return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"

    def _extract_primary_label(self, question: str) -> str | None:
        for label in KNOWN_PRIMARY_LABELS:
            if self._contains_label_text(question, label):
                return label
        return None

    def _extract_tertiary_label(self, question: str) -> str | None:
        for label in KNOWN_TERTIARY_LABELS:
            if self._contains_any_label_text(question, tertiary_label_variants(label)):
                return label
        return None

    def _fields_from_dsl(self, node: Any) -> list[str]:
        fields: list[str] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                if isinstance(value.get("field"), str) and self._is_allowed_field(value["field"]):
                    fields.append(value["field"])
                for key, item in value.items():
                    if key in FIELD_CLAUSES and isinstance(item, dict) and "field" not in item:
                        for field in item:
                            if self._is_allowed_field(str(field)):
                                fields.append(str(field))
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(node)
        return list(dict.fromkeys(fields))

    def build_query(self, intent: dict[str, Any]) -> dict[str, Any]:
        body = copy.deepcopy(intent.get("query") if "query" in intent else intent)
        if not isinstance(body, dict):
            raise InvalidQueryError("查询 DSL 必须是 JSON 对象。")
        if not body:
            raise InvalidQueryError("查询 DSL 不能为空。")

        if not any(key in TOP_LEVEL_KEYS for key in body):
            body = {"query": body}

        unknown = set(body) - TOP_LEVEL_KEYS
        if unknown:
            raise InvalidQueryError("查询 DSL 含有不允许的顶层字段：" + "、".join(sorted(unknown)))

        if not any(key in body for key in ("query", "aggs", "aggregations")):
            raise InvalidQueryError("查询 DSL 至少需要包含 query 或 aggs/aggregations。")

        size = body.get("size", 0 if any(key in body for key in ("aggs", "aggregations")) else 10)
        try:
            size = int(size)
        except (TypeError, ValueError) as exc:
            raise InvalidQueryError("size 必须是整数。") from exc
        body["size"] = max(0, min(size, self.max_size))
        body["track_total_hits"] = True
        body["timeout"] = "10s"
        if body["size"] > 0:
            body["_source"] = self._sanitize_source(body.get("_source"))
            body.setdefault("sort", [{"service_time": {"order": "desc"}}])

        self._normalize_field_usage(body)
        self._enrich_date_histogram_aggs(body)
        self._validate_safety(body)
        self._validate_sort(body.get("sort"))
        return body

    def execute_query(self, query: dict[str, Any]) -> dict[str, Any]:
        if not self.es.indices.exists(index=self.index_name):
            raise ElasticsearchError(f"Elasticsearch 索引不存在：{self.index_name}")
        _, payload = self.es.request(
            "POST",
            f"/{self.index_name}/_search",
            body=query,
            params={"timeout": "10s"},
            timeout_seconds=10,
        )
        return payload

    def execute_intent(self, intent: dict[str, Any]) -> dict[str, Any]:
        if (intent.get("metadata") or {}).get("intent_type") == "tertiary_top_cause_analysis":
            if not self.es.indices.exists(index=self.index_name):
                raise ElasticsearchError(f"Elasticsearch 索引不存在：{self.index_name}")
            query = (intent.get("query") or {}).get("query") or {"match_all": {}}
            return {
                "_evidence_package": build_tertiary_evidence_package(
                    self.es,
                    self.index_name,
                    query,
                    top_n=5,
                )
            }
        return self.execute_query(intent["query"])

    def parse_results(self, results: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
        if "_evidence_package" in results:
            package = results.get("_evidence_package") or {}
            return {
                "took": None,
                "timed_out": False,
                "hits_total": package.get("doc_total", 0),
                "hits": [],
                "aggregations": {},
                "evidence_package": package,
                "explanation": intent.get("explanation"),
                "expected_fields": intent.get("expected_fields", []),
            }
        hits = results.get("hits", {})
        total = hits.get("total", 0)
        total_value = total.get("value", 0) if isinstance(total, dict) else total
        return {
            "took": results.get("took"),
            "timed_out": results.get("timed_out", False),
            "hits_total": total_value,
            "hits": self._compact_hits(hits.get("hits", []), limit=10),
            "aggregations": self._compact_aggs(results.get("aggregations") or results.get("aggs") or {}),
            "explanation": intent.get("explanation"),
            "expected_fields": intent.get("expected_fields", []),
        }

    def summarize_results(self, parsed_results: dict[str, Any]) -> dict[str, Any]:
        if parsed_results.get("evidence_package"):
            return self._summarize_evidence_package(parsed_results["evidence_package"])
        aggregations = parsed_results.get("aggregations") or {}
        summaries = []
        for name, agg in aggregations.items():
            summaries.append(self._summarize_aggregation(name, agg, parsed_results.get("hits_total", 0)))
        return {
            "executed": True,
            "hits_total": parsed_results.get("hits_total", 0),
            "timed_out": parsed_results.get("timed_out", False),
            "aggregations": summaries,
            "sample_count": len(parsed_results.get("hits", [])),
        }

    def _summarize_evidence_package(self, package: dict[str, Any]) -> dict[str, Any]:
        items = []
        for item in package.get("items", []):
            if not isinstance(item, dict):
                continue
            children = {}
            for key in ("top_customer_appeals", "top_customer_keywords", "top_cs_actions", "top_cs_keywords"):
                buckets = []
                for bucket in item.get(key, [])[:10]:
                    if not isinstance(bucket, dict):
                        continue
                    buckets.append(
                        {
                            "key": bucket.get("key"),
                            "count": int(bucket.get("count") or 0),
                        }
                    )
                if buckets:
                    children[key] = buckets
            row = {
                "key": item.get("key"),
                "count": int(item.get("count") or 0),
                "share": float(item.get("share") or 0),
                "sample_count": len(item.get("samples") or []),
            }
            if children:
                row["children"] = children
            items.append(row)

        sample_count = sum(int(item.get("sample_count") or 0) for item in items)
        return {
            "executed": True,
            "hits_total": int(package.get("doc_total") or 0),
            "timed_out": False,
            "evidence_package": {
                "intent_type": package.get("intent_type"),
                "tertiary_total": int(package.get("tertiary_total") or 0),
                "top_n": int(package.get("top_n") or 0),
                "samples_per_label": int(package.get("samples_per_label") or 0),
                "sample_strategy": package.get("sample_strategy") or {},
            },
            "aggregations": [
                {
                    "name": "top_tertiary_cause_analysis",
                    "type": "terms",
                    "source_field": "tertiary_labels",
                    "bucket_total": int(package.get("tertiary_total") or 0),
                    "share_denominator": int(package.get("tertiary_total") or 0) or 1,
                    "top": items[0] if items else None,
                    "items": items,
                }
            ],
            "sample_count": sample_count,
        }

    def _finalize_intent(self, intent: dict[str, Any]) -> dict[str, Any]:
        intent = copy.deepcopy(intent)
        intent["query"] = self.build_query(intent)
        intent["expected_fields"] = self._sanitize_expected_fields(intent.get("expected_fields"))
        intent["explanation"] = str(intent.get("explanation") or "已生成只读 Elasticsearch 查询。")
        return intent

    def _distribution_intent(self, question: str, spec: dict[str, Any]) -> dict[str, Any]:
        filters = self._question_filters(question, exclude_fields={spec["field"]})
        body = {
            "size": 0,
            "query": self._filter_query(filters),
            "aggs": {
                spec["agg_name"]: {
                    "terms": {
                        "field": spec["field"],
                        "size": 50,
                    }
                }
            },
        }
        return {
            "query": body,
            "explanation": f"按 {spec['label']} 统计分布，并返回各桶数量用于计算占比。",
            "expected_fields": [spec["field"]],
            "metadata": {"deterministic": True, "aggregation_field": spec["field"]},
        }

    def _is_tertiary_top_cause_question(self, question: str) -> bool:
        if "三级" not in question and "tertiary" not in question.lower():
            return False
        if not any(term in question for term in TOP_TERMS):
            return False
        return any(term in question for term in CAUSE_TERMS)

    def _tertiary_top_cause_intent(self, question: str) -> dict[str, Any]:
        filters = self._question_filters(question)
        body = {
            "size": 0,
            "query": self._filter_query(filters),
            "aggs": {
                "top_tertiary_cause_analysis": {
                    "terms": {
                        "field": "tertiary_labels",
                        "size": 5,
                    }
                }
            },
        }
        return {
            "query": body,
            "explanation": (
                "先统计数量最多的五个三级标签；执行阶段会为每个 TOP 三级标签继续抽取工单内容、客服回复、"
                "客户诉求和客服处理动作证据包，再用于原因分析。"
            ),
            "expected_fields": EVIDENCE_SOURCE_FIELDS,
            "metadata": {
                "deterministic": True,
                "intent_type": "tertiary_top_cause_analysis",
                "aggregation_field": "tertiary_labels",
            },
        }

    def _trend_intent(self, question: str, last_query_dsl: dict[str, Any] | None = None) -> dict[str, Any]:
        filters = self._question_filters(question)
        previous_query = None
        if not filters and any(term in question for term in FOLLOWUP_TERMS):
            previous_query = self._previous_query(last_query_dsl)
        body = {
            "size": 0,
            "query": previous_query or self._filter_query(filters),
            "aggs": {
                "daily_trend": {
                    "date_histogram": {
                        "field": "service_time",
                        "calendar_interval": "day",
                        "format": "yyyy-MM-dd",
                        "min_doc_count": 1,
                    },
                    "aggs": {
                        "top_primary_labels": {"terms": {"field": "primary_labels", "size": 5}},
                        "top_secondary_labels": {"terms": {"field": "secondary_labels", "size": 5}},
                        "top_tertiary_labels": {"terms": {"field": "tertiary_labels", "size": 5}},
                        "top_operations": {"terms": {"field": "operation_action", "size": 5}},
                        "top_member_clusters": {"terms": {"field": "biz_member_cluster", "size": 5}},
                        "top_matches": {"terms": {"field": "match_label", "size": 5}},
                    },
                }
            },
        }
        return {
            "query": body,
            "explanation": "按天统计投诉/工单数量趋势，并在每个日期桶下聚合主要一级、二级、三级标签。",
            "expected_fields": ["service_time", "primary_labels", "secondary_labels", "tertiary_labels"],
            "metadata": {"deterministic": True, "aggregation_field": "service_time"},
        }

    def _detail_intent(self, question: str, filters: list[dict[str, Any]]) -> dict[str, Any]:
        body = {
            "size": min(self.max_size, 30),
            "query": self._filter_query(filters),
            "_source": DEFAULT_SOURCE_FIELDS,
            "sort": [{"service_time": {"order": "desc"}}],
        }
        return {
            "query": body,
            "explanation": "根据问题中的业务字段和关键词过滤相关工单，并返回样例明细用于查看典型案例。",
            "expected_fields": DEFAULT_SOURCE_FIELDS,
            "metadata": {"deterministic": True, "detail_query": True},
        }

    def _build_contextual_followup_intent(
        self,
        question: str,
        last_query_summary: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not last_query_summary:
            return None
        if not any(term in question for term in ("最高", "最多", "第一", "那个", "这个", "该")):
            return None
        if not any(term in question for term in ("诉求", "问题", "原因", "明细", "样例", "主要")):
            return None

        top_bucket = self._find_last_top_bucket(last_query_summary)
        if not top_bucket:
            return None

        source_field = top_bucket["source_field"]
        source_value = top_bucket["key"]
        if "诉求" in question or "原因" in question or "主要" in question:
            agg_field = "customer_key_appeal.keyword"
            agg_name = "top_customer_appeals"
            label = "用户核心诉求"
        else:
            agg_field = "tertiary_labels"
            agg_name = "top_related_tertiary_labels"
            label = "相关三级标签"

        body = {
            "size": 0,
            "query": {"term": {source_field: source_value}},
            "aggs": {
                agg_name: {
                    "terms": {
                        "field": agg_field,
                        "size": 10,
                    }
                }
            },
        }
        return {
            "query": body,
            "explanation": f"承接上一轮最高项“{source_value}”，过滤 {source_field} 后统计主要{label}。",
            "expected_fields": [source_field, agg_field],
            "metadata": {
                "deterministic": True,
                "context_source_field": source_field,
                "context_source_value": source_value,
                "aggregation_field": agg_field,
            },
        }

    def _question_filters(self, question: str, exclude_fields: set[str] | None = None) -> list[dict[str, Any]]:
        exclude_fields = exclude_fields or set()
        filters: list[dict[str, Any]] = []
        if "primary_labels" not in exclude_fields:
            for primary_label in KNOWN_PRIMARY_LABELS:
                if self._contains_label_text(question, primary_label):
                    filters.append({"term": {"primary_labels": primary_label}})
                    break
        if "tertiary_labels" not in exclude_fields:
            for tertiary_label in KNOWN_TERTIARY_LABELS:
                if self._contains_any_label_text(question, tertiary_label_variants(tertiary_label)):
                    filters.append(self._label_terms_filter("tertiary_labels", tertiary_label_variants(tertiary_label)))
                    break
        if "投诉" in question:
            filters.append({"term": {"scene_service_type": "投诉"}})
        if "退费" in question or "退款" in question:
            filters.append({"term": {"has_refund_demand": "是"}})
        if "升级投诉" in question or "升级" in question:
            filters.append({"term": {"has_escalation": "是"}})
        if "tertiary_labels" not in exclude_fields and ("误订购" in question or "不知情订购" in question):
            filters.append(
                {
                    "bool": {
                        "should": [
                            {"term": {"tertiary_labels": "不知情订购"}},
                            {"match_phrase": {"content": "误订购"}},
                            {"match_phrase": {"complaint_content": "误订购"}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        for operation in KNOWN_OPERATIONS:
            if operation in question:
                filters.append({"term": {"operation_action": operation}})
        for cluster in KNOWN_MEMBER_CLUSTERS:
            if cluster in question:
                filters.append({"term": {"biz_member_cluster": cluster}})
        for dimension in KNOWN_INSIGHT_DIMENSIONS:
            if dimension in question:
                filters.append({"term": {"insight_dimension": dimension}})
        for period in KNOWN_TIME_PERIODS:
            if period in question:
                filters.append({"term": {"time_period": period}})
        return filters

    def _contains_any_label_text(self, question: str, labels: tuple[str, ...]) -> bool:
        return any(self._contains_label_text(question, label) for label in labels if label)

    def _contains_label_text(self, question: str, label: str) -> bool:
        if label in question:
            return True
        compact_question = self._compact_label_text(question)
        compact_label = self._compact_label_text(label)
        return bool(compact_label and compact_label in compact_question)

    def _compact_label_text(self, value: Any) -> str:
        text = str(value or "")
        return re.sub(r"[\s/、，,（）()]+", "", text)

    def _label_terms_filter(self, field: str, labels: tuple[str, ...]) -> dict[str, Any]:
        values: list[str] = []
        for label in labels:
            canonical = canonical_tertiary_label(label)
            if canonical:
                values.append(canonical)
            if label:
                values.append(label)
        values = list(dict.fromkeys(values))
        if not values:
            return {"match_all": {}}
        if len(values) == 1:
            return {"term": {field: values[0]}}
        return {
            "bool": {
                "should": [{"term": {field: value}} for value in values],
                "minimum_should_match": 1,
            }
        }

    def _filter_query(self, filters: list[dict[str, Any]]) -> dict[str, Any]:
        if not filters:
            return {"match_all": {}}
        if len(filters) == 1:
            return filters[0]
        return {"bool": {"filter": filters}}

    def _previous_query(self, last_query_dsl: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(last_query_dsl, dict):
            return None
        query = last_query_dsl.get("query")
        if not isinstance(query, dict) or query == {"match_all": {}}:
            return None
        return copy.deepcopy(query)

    def _find_last_top_bucket(self, result_summary: dict[str, Any]) -> dict[str, Any] | None:
        for agg in result_summary.get("aggregations", []):
            if not isinstance(agg, dict) or agg.get("type") != "terms":
                continue
            top = agg.get("top")
            source_field = agg.get("source_field")
            if isinstance(top, dict) and top.get("key") not in (None, "") and source_field:
                return {"source_field": source_field, "key": top["key"]}
        return None

    def _normalize_field_usage(self, node: Any, parent_key: str | None = None) -> None:
        if isinstance(node, dict):
            for key, value in list(node.items()):
                if key == "field" and isinstance(value, str) and value in KEYWORD_FIELD_REWRITES:
                    node[key] = KEYWORD_FIELD_REWRITES[value]
                    continue
                if isinstance(key, str) and parent_key in {"term", "terms", "sort"} and key in KEYWORD_FIELD_REWRITES:
                    node[KEYWORD_FIELD_REWRITES[key]] = node.pop(key)
                    value = node[KEYWORD_FIELD_REWRITES[key]]
                    key = KEYWORD_FIELD_REWRITES[key]
                self._normalize_field_usage(value, parent_key=str(key))
        elif isinstance(node, list):
            for item in node:
                self._normalize_field_usage(item, parent_key=parent_key)

    def analyze_results(
        self,
        question: str,
        parsed_results: dict[str, Any],
        intent: dict[str, Any],
        result_summary: dict[str, Any] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        if self._is_empty(parsed_results):
            return "未找到匹配数据。建议换一个日期范围、问题标签或关键词后再试。"
        if not self.llm.enabled:
            return self._fallback_answer(parsed_results, result_summary=result_summary)

        result_summary = result_summary or self.summarize_results(parsed_results)
        payload = {
            "executed": True,
            "index_name": self.index_name,
            "question": question,
            "query_explanation": intent.get("explanation"),
            "intent_metadata": intent.get("metadata", {}),
            "query_dsl": intent.get("query"),
            "result_summary": result_summary,
            "results": parsed_results,
        }
        payload_text = json.dumps(payload, ensure_ascii=False)
        payload_limit = (
            MAX_EVIDENCE_PAYLOAD_CHARS
            if (intent.get("metadata") or {}).get("intent_type") == "tertiary_top_cause_analysis"
            else 12000
        )
        if len(payload_text) > payload_limit:
            payload_text = payload_text[:payload_limit] + "...(已截断)"

        response = self.llm.chat(
            [
                {"role": "system", "content": ANALYSIS_PROMPT},
                *(history or [])[-8:],
                {
                    "role": "system",
                    "content": "下面用户消息是当前刚执行完成的 Elasticsearch 结果。请直接回答当前 question，并列出本次结果中的关键数字。",
                },
                {"role": "user", "content": payload_text},
            ],
            temperature=0.2,
        )
        if response.used_fallback or not response.content.strip():
            return self._fallback_answer(parsed_results, result_summary=result_summary)
        answer = response.content.strip()
        if self._is_unhelpful_analysis(answer):
            return self._fallback_answer(parsed_results, result_summary=result_summary)
        return answer

    def _enrich_date_histogram_aggs(self, body: dict[str, Any]) -> None:
        aggs = body.get("aggs") or body.get("aggregations")
        if isinstance(aggs, dict):
            self._enrich_date_histogram_node(aggs)

    def _enrich_date_histogram_node(self, node: dict[str, Any]) -> None:
        for agg_body in node.values():
            if not isinstance(agg_body, dict):
                continue
            if "date_histogram" in agg_body:
                child_aggs = agg_body.setdefault("aggs", {})
                child_aggs.setdefault("top_primary_labels", {"terms": {"field": "primary_labels", "size": 5}})
                child_aggs.setdefault("top_secondary_labels", {"terms": {"field": "secondary_labels", "size": 5}})
                child_aggs.setdefault("top_tertiary_labels", {"terms": {"field": "tertiary_labels", "size": 5}})
                child_aggs.setdefault("top_operations", {"terms": {"field": "operation_action", "size": 5}})
                child_aggs.setdefault("top_member_clusters", {"terms": {"field": "biz_member_cluster", "size": 5}})
                child_aggs.setdefault("top_matches", {"terms": {"field": "match_label", "size": 5}})
            child = agg_body.get("aggs") or agg_body.get("aggregations")
            if isinstance(child, dict):
                self._enrich_date_histogram_node(child)

    def _sanitize_source(self, value: Any) -> list[str]:
        if value is None or value is True:
            return DEFAULT_SOURCE_FIELDS
        if value is False:
            return []
        if not isinstance(value, list):
            raise InvalidQueryError("_source 只能是字段列表或布尔值。")
        return self._sanitize_expected_fields(value)[: len(DEFAULT_SOURCE_FIELDS)] or DEFAULT_SOURCE_FIELDS

    def _sanitize_expected_fields(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        fields = []
        for item in value:
            field = str(item).strip()
            if field and self._is_allowed_field(field):
                fields.append(field)
        return fields

    def _validate_safety(self, node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_text = str(key)
                if key_text in BANNED_KEYS or key_text.startswith("_") and key_text not in {"_source", "_count", "_key"}:
                    raise InvalidQueryError(f"查询 DSL 含有不允许的字段或能力：{key_text}")

                if key_text in FIELD_CLAUSES and isinstance(value, dict) and "field" not in value:
                    self._validate_field_clause(key_text, value)
                if key_text == "multi_match" and isinstance(value, dict):
                    fields = value.get("fields")
                    if not isinstance(fields, list) or not fields:
                        raise InvalidQueryError("multi_match 必须显式指定允许的 fields。")
                    for field in fields:
                        self._require_allowed_field(str(field).split("^", 1)[0])
                if key_text == "exists" and isinstance(value, dict) and "field" in value:
                    self._require_allowed_field(value["field"])
                if key_text == "field":
                    self._require_allowed_field(value)

                self._validate_safety(value)
        elif isinstance(node, list):
            for item in node:
                self._validate_safety(item)

    def _validate_field_clause(self, clause: str, value: dict[str, Any]) -> None:
        if clause == "exists":
            return
        for field in value:
            self._require_allowed_field(field)

    def _validate_sort(self, sort: Any) -> None:
        if sort is None:
            return
        if not isinstance(sort, list):
            raise InvalidQueryError("sort 必须是列表。")
        for item in sort:
            if isinstance(item, str):
                self._require_allowed_field(item)
            elif isinstance(item, dict):
                for field in item:
                    self._require_allowed_field(field)
            else:
                raise InvalidQueryError("sort 中包含不支持的元素。")

    def _require_allowed_field(self, field: Any) -> None:
        if not isinstance(field, str) or not self._is_allowed_field(field):
            raise InvalidQueryError(f"字段不在允许范围内：{field}")

    def _is_allowed_field(self, field: str) -> bool:
        if field in self.allowed_fields:
            return True
        if field.endswith(".keyword") and field[:-8] in self.allowed_fields:
            return True
        return False

    def _compact_hits(self, hits: list[dict], limit: int) -> list[dict[str, Any]]:
        compact = []
        for hit in hits[:limit]:
            source = hit.get("_source", {})
            if not isinstance(source, dict):
                continue
            compact.append({field: self._clip_value(source.get(field)) for field in DEFAULT_SOURCE_FIELDS if source.get(field) not in (None, "")})
        return compact

    def _compact_aggs(self, aggs: Any, depth: int = 0) -> Any:
        if depth > 4:
            return "(聚合层级已截断)"
        if isinstance(aggs, dict):
            if "buckets" in aggs and isinstance(aggs["buckets"], list):
                buckets = []
                for bucket in aggs["buckets"][:20]:
                    item = {
                        "key": bucket.get("key_as_string", bucket.get("key")),
                        "doc_count": bucket.get("doc_count"),
                    }
                    for key, value in bucket.items():
                        if key in {"key", "key_as_string", "doc_count"}:
                            continue
                        item[key] = self._compact_aggs(value, depth + 1)
                    buckets.append(item)
                return {"buckets": buckets}
            if "hits" in aggs and isinstance(aggs["hits"], dict):
                return {"hits": self._compact_hits(aggs["hits"].get("hits", []), limit=5)}
            return {key: self._compact_aggs(value, depth + 1) for key, value in aggs.items() if key != "meta"}
        if isinstance(aggs, list):
            return [self._compact_aggs(item, depth + 1) for item in aggs[:20]]
        return self._clip_value(aggs)

    def _clip_value(self, value: Any) -> Any:
        if isinstance(value, str) and len(value) > 240:
            return value[:239].rstrip() + "..."
        return value

    def _summarize_aggregation(self, name: str, agg: Any, hits_total: int | None = None) -> dict[str, Any]:
        if not isinstance(agg, dict) or not isinstance(agg.get("buckets"), list):
            return {"name": name, "type": "metric_or_nested", "value": agg}

        buckets = [bucket for bucket in agg.get("buckets", []) if isinstance(bucket, dict)]
        is_date_histogram = all(DATE_KEY_PATTERN.match(str(bucket.get("key", ""))) for bucket in buckets) if buckets else False
        if is_date_histogram:
            return self._summarize_date_histogram(name, buckets)
        return self._summarize_terms(name, buckets, hits_total=hits_total)

    def _summarize_terms(self, name: str, buckets: list[dict[str, Any]], hits_total: int | None = None) -> dict[str, Any]:
        total = sum(int(bucket.get("doc_count", 0) or 0) for bucket in buckets)
        denominator = int(hits_total or 0) or total or 1
        items = []
        for bucket in buckets[:20]:
            count = int(bucket.get("doc_count", 0) or 0)
            item = {
                "key": bucket.get("key"),
                "count": count,
                "share": round(count / denominator, 4) if denominator else 0,
            }
            children = self._summarize_bucket_children(bucket)
            if children:
                item["children"] = children
            items.append(item)
        return {
            "name": name,
            "type": "terms",
            "source_field": self._infer_source_field(name),
            "bucket_total": total,
            "share_denominator": denominator,
            "top": items[0] if items else None,
            "items": items,
        }

    def _infer_source_field(self, agg_name: str) -> str | None:
        lowered = agg_name.lower()
        hints = [
            (("tertiary", "三级"), "tertiary_labels"),
            (("secondary", "二级"), "secondary_labels"),
            (("primary", "一级"), "primary_labels"),
            (("emotion", "情绪"), "scene_emotion"),
            (("province", "省份", "地区", "地域"), "province_name"),
            (("appeal", "诉求"), "customer_key_appeal.keyword"),
            (("cs_action", "客服动作", "处理动作", "客服处理"), "cs_key_action.keyword"),
            (("operation", "运营", "活动", "举措"), "operation_action"),
            (("marketing", "营销", "页面"), "marketing_activity_page"),
            (("match_status", "匹配状态"), "marketing_activity_match_status"),
            (("keyword", "关键词"), "marketing_activity_match_keywords"),
            (("member", "cluster", "会员", "聚类"), "biz_member_cluster"),
            (("latent", "隐性", "潜在"), "latent_need.keyword"),
            (("match", "比赛", "赛事"), "match_label"),
            (("period", "时段"), "time_period"),
            (("age", "年龄"), "age"),
            (("gender", "性别"), "gender"),
            (("label_group", "标签组"), "label_group"),
        ]
        for markers, field in hints:
            if any(marker in lowered or marker in agg_name for marker in markers):
                return field
        return None

    def _summarize_date_histogram(self, name: str, buckets: list[dict[str, Any]]) -> dict[str, Any]:
        items = [
            {
                "date": bucket.get("key"),
                "count": int(bucket.get("doc_count", 0) or 0),
                "top_labels": self._summarize_bucket_children(bucket),
            }
            for bucket in buckets
        ]
        peak = max(items, key=lambda item: item["count"], default=None)
        nonzero = [item for item in items if item["count"] > 0]
        trough = min(nonzero, key=lambda item: item["count"], default=None)
        anomalies = []
        previous: dict[str, Any] | None = None
        for item in items:
            if previous and previous["count"] > 0:
                growth = (item["count"] - previous["count"]) / previous["count"]
                if growth >= 0.5 and item["count"] >= 5:
                    anomalies.append(
                        {
                            "date": item["date"],
                            "count": item["count"],
                            "previous_date": previous["date"],
                            "previous_count": previous["count"],
                            "growth": round(growth, 4),
                            "top_labels": item["top_labels"],
                        }
                    )
            previous = item
        return {
            "name": name,
            "type": "date_histogram",
            "bucket_count": len(items),
            "total_count": sum(item["count"] for item in items),
            "peak": peak,
            "trough": trough,
            "anomalies": anomalies[:10],
            "items": items[:60],
        }

    def _summarize_bucket_children(self, bucket: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        children: dict[str, list[dict[str, Any]]] = {}
        for key, value in bucket.items():
            if key in {"key", "key_as_string", "doc_count"}:
                continue
            if isinstance(value, dict) and isinstance(value.get("buckets"), list):
                child_buckets = []
                child_total = sum(int(child.get("doc_count", 0) or 0) for child in value["buckets"]) or 1
                for child in value["buckets"][:10]:
                    count = int(child.get("doc_count", 0) or 0)
                    child_buckets.append(
                        {
                            "key": child.get("key"),
                            "count": count,
                            "share": round(count / child_total, 4),
                        }
                    )
                children[key] = child_buckets
        return children

    def _is_empty(self, parsed_results: dict[str, Any]) -> bool:
        if int(parsed_results.get("hits_total") or 0) > 0:
            return False
        return not bool(parsed_results.get("aggregations"))

    def _fallback_answer(self, parsed_results: dict[str, Any], result_summary: dict[str, Any] | None = None) -> str:
        total = int(parsed_results.get("hits_total") or 0)
        if result_summary:
            formatted = self._format_summary_answer(result_summary)
            if formatted:
                return formatted
            return "查询已完成。结构化摘要如下：\n" + json.dumps(result_summary, ensure_ascii=False, indent=2)[:4000]
        aggs = parsed_results.get("aggregations") or {}
        if aggs:
            return "查询已完成。命中总量为 {} 条，聚合结果如下：\n{}".format(
                total,
                json.dumps(aggs, ensure_ascii=False, indent=2)[:4000],
            )
        return f"查询已完成，命中总量为 {total} 条。"

    def _is_unhelpful_analysis(self, answer: str) -> bool:
        hard_prohibited = (
            "无法直接执行 Elasticsearch 查询",
            "请运维执行",
            "请有查询权限",
        )
        if any(phrase in answer for phrase in hard_prohibited):
            return True
        weak_phrases = (
            "已完整展示",
            "如需进一步分析",
            "请随时告知",
        )
        if any(phrase in answer for phrase in weak_phrases) and not re.search(r"\d", answer):
            return True
        return not re.search(r"\d", answer)

    def _format_summary_answer(self, result_summary: dict[str, Any]) -> str:
        aggregations = result_summary.get("aggregations") or []
        for agg in aggregations:
            if isinstance(agg, dict) and agg.get("name") == "top_tertiary_cause_analysis":
                return self._format_tertiary_cause_answer(agg, int(result_summary.get("hits_total") or 0))
        for agg in aggregations:
            if isinstance(agg, dict) and agg.get("type") == "date_histogram":
                return self._format_date_histogram_answer(agg)
        for agg in aggregations:
            if isinstance(agg, dict) and agg.get("type") == "terms":
                return self._format_terms_answer(agg, int(result_summary.get("hits_total") or 0))
        return ""

    def _format_terms_answer(self, agg: dict[str, Any], hits_total: int) -> str:
        items = [item for item in agg.get("items", []) if isinstance(item, dict)]
        if not items:
            return ""
        lines = [f"查询已执行，共命中 {hits_total} 条。{agg.get('name', '聚合')} 分布如下："]
        for item in items[:15]:
            share = float(item.get("share") or 0) * 100
            lines.append(f"- {item.get('key')}：{item.get('count')} 条，占比 {share:.2f}%")
        return "\n".join(lines)

    def _format_tertiary_cause_answer(self, agg: dict[str, Any], hits_total: int) -> str:
        items = [item for item in agg.get("items", []) if isinstance(item, dict)]
        if not items:
            return ""
        lines = [f"查询已执行，共命中 {hits_total} 条。数量最多的五个三级标签为："]
        for index, item in enumerate(items[:5], start=1):
            count = int(item.get("count") or 0)
            share = float(item.get("share") or 0) * 100
            lines.append(f"{index}. {item.get('key')}：{count} 条，占比 {share:.2f}%")
            children = item.get("children") if isinstance(item.get("children"), dict) else {}
            appeals = "、".join(str(bucket.get("key")) for bucket in children.get("top_customer_appeals", [])[:3]) or "无"
            customer_keywords = "、".join(str(bucket.get("key")) for bucket in children.get("top_customer_keywords", [])[:4]) or "无"
            cs_actions = "、".join(str(bucket.get("key")) for bucket in children.get("top_cs_actions", [])[:3]) or "无"
            cs_keywords = "、".join(str(bucket.get("key")) for bucket in children.get("top_cs_keywords", [])[:4]) or "无"
            lines.append("   - 工单内容与客服回复：已抽取该标签下代表性工单正文和客服回复，启用 DeepSeek 时会进一步压缩为自然语言场景总结。")
            lines.append(f"   - 客户关键诉求与客户诉求关键词：主要客户诉求为 {appeals}；诉求关键词集中在 {customer_keywords}。")
            lines.append(f"   - 客服关键处理动作与客服处理关键词：客服处理动作集中在 {cs_actions}；处理关键词集中在 {cs_keywords}。")
        lines.append("当前未启用大模型时只能给出结构化原因线索；启用 DeepSeek 后会把样例工单和客服回复整合成自然语言原因分析。")
        return "\n".join(lines)

    def _format_date_histogram_answer(self, agg: dict[str, Any]) -> str:
        peak = agg.get("peak") if isinstance(agg.get("peak"), dict) else None
        if not peak:
            return ""
        lines = [
            f"查询已执行，共统计 {agg.get('total_count', 0)} 条记录，覆盖 {agg.get('bucket_count', 0)} 个日期桶。",
            f"峰值日是 {peak.get('date')}，当天 {peak.get('count')} 条。",
        ]
        top_labels = self._format_child_labels(peak.get("top_labels"), peak_count=int(peak.get("count") or 0))
        if top_labels:
            lines.append("峰值日主要问题：")
            lines.extend(top_labels)
        anomalies = [item for item in agg.get("anomalies", []) if isinstance(item, dict)]
        if anomalies:
            lines.append("明显异动日：")
            for item in anomalies[:5]:
                growth = float(item.get("growth") or 0) * 100
                lines.append(
                    f"- {item.get('date')}：{item.get('count')} 条，较 {item.get('previous_date')} "
                    f"{item.get('previous_count')} 条增长 {growth:.1f}%"
                )
        return "\n".join(lines)

    def _format_child_labels(self, top_labels: Any, peak_count: int) -> list[str]:
        if not isinstance(top_labels, dict):
            return []
        label_names = {
            "top_primary_labels": "一级标签",
            "top_secondary_labels": "二级标签",
            "top_tertiary_labels": "三级标签",
            "top_operations": "运营举措",
            "top_member_clusters": "会员类型",
            "top_matches": "比赛信息",
        }
        lines = []
        for key, label in label_names.items():
            buckets = [item for item in top_labels.get(key, []) if isinstance(item, dict)]
            if not buckets:
                continue
            parts = []
            for item in buckets[:3]:
                count = int(item.get("count") or 0)
                share = count / peak_count * 100 if peak_count else 0
                parts.append(f"{item.get('key')} {count} 条（{share:.1f}%）")
            lines.append(f"- {label}：" + "，".join(parts))
        return lines
