from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

from .agent import OverallSituationAgent
from .config import Settings
from .es_query_builder import ESQueryBuilder, ESQueryError, LLMUnavailableError
from .llm_client import OpenAICompatibleClient, parse_json_object
from .output_naming import make_report_path
from .query_planner import DATE_PATTERN, QueryPlan
from .state import AgentState

logger = logging.getLogger(__name__)


HELP_TEXT = """
普通输入：
  涉及工单/投诉/标签/趋势等数据问题时，会生成 Elasticsearch 查询并基于结果回答
  不涉及数据查询的问题，会作为普通对话直接回答，不生成文档

内置命令：
  /help      查看提示
  /context   查看当前会话状态
  /exit      退出
  /report    生成完整“一、整体情况”报告（支持加日期范围）

示例：
  列出你能做什么
  业务体验有多少条？
  最近有哪些退订困难自动续费争议？
  /report
  /report 2026-01-01 到 2026-01-31
""".strip()


DATA_QUERY_TERMS = [
    "工单",
    "投诉",
    "反馈",
    "数据",
    "查询",
    "top",
    "TOP",
    "前五",
    "前5",
    "多少",
    "几条",
    "有哪些",
    "列出",
    "明细",
    "分布",
    "趋势",
    "异动",
    "情绪",
    "省份",
    "标签",
    "一级",
    "二级",
    "三级",
    "退费",
    "权益",
    "订购",
    "业务体验",
    "内容体验",
    "营销活动",
    "营销",
    "营销活动页面",
    "匹配状态",
    "匹配关键词",
    "标签组",
    "客服动作",
    "客服处理",
    "客服回复",
    "处理意见",
    "客户诉求",
    "原因",
    "短板",
    "年龄",
    "性别",
    "使用体验",
]

CONTEXT_QUERY_TERMS = [
    "刚才",
    "上一个",
    "上一条",
    "你说的",
    "按照你说的",
    "继续",
    "验证",
    "这个",
    "那个",
    "最高",
    "最低",
    "主要",
    "它",
    "该",
    "date_histogram",
    "聚合",
]

HISTORY_QUERY_PATTERNS = [
    re.compile(r"上一个问题"),
    re.compile(r"上一条问题"),
    re.compile(r"上一轮"),
    re.compile(r"一开始"),
    re.compile(r"最开始"),
    re.compile(r"最早.*问"),
    re.compile(r"第一个问题"),
    re.compile(r"第[一二三四五六七八九十\d]+.*(问题|轮|次)"),
    re.compile(r"(刚才|之前|刚刚).*(问|说|提)"),
    re.compile(r"刚才聊了什么"),
    re.compile(r"之前聊了什么"),
]

_CHINESE_NUM_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _chinese_to_int(token: str) -> int:
    if token.isdigit():
        return int(token)
    return _CHINESE_NUM_MAP.get(token, 0)

NORMAL_CHAT_TERMS = [
    "你能做什么",
    "能做什么",
    "你是谁",
    "介绍你自己",
    "怎么用",
    "使用说明",
    "帮助",
    "help",
]

REPORT_REQUEST_TERMS = [
    "生成报告",
    "生成整体情况报告",
    "生成整体情况",
    "出报告",
    "制作报告",
    "导出报告",
]

CONSOLE_TEXT_REPLACEMENTS = {
    "\u00a0": " ",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
}


def _normalize_input_text(input_text: str) -> str:
    """Recover UTF-8 text that was decoded as GBK/CP936 in Windows pipes."""
    if not input_text:
        return input_text
    try:
        recovered = input_text.encode("gbk", errors="surrogateescape").decode("utf-8")
    except UnicodeError:
        return input_text
    if recovered != input_text and any("\u4e00" <= char <= "\u9fff" for char in recovered):
        return recovered
    return input_text


def _sanitize_console_text(text: str) -> str:
    for source, target in CONSOLE_TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    encoding = sys.stdout.encoding or "utf-8"
    try:
        return text.encode(encoding, errors="replace").decode(encoding)
    except LookupError:
        return text


def _is_report_request_text(question: str) -> bool:
    return any(term in question for term in REPORT_REQUEST_TERMS)


def _validate_chat_question(question: str) -> list[str]:
    errors = []
    cleaned = question.strip()
    if not cleaned:
        errors.append("问题不能为空。")
    if len(cleaned) > 300:
        errors.append("问题过长，请控制在 300 字以内。")
    if re.search(r"<script|</html|<iframe", cleaned, flags=re.IGNORECASE):
        errors.append("问题中包含不允许的 HTML/脚本片段。")
    return errors


class InteractiveOverallSituationApp:
    def __init__(self, settings: Settings, schedule_input: Path | None = None):
        self.settings = settings
        self.agent = OverallSituationAgent(settings)
        self.llm = OpenAICompatibleClient(settings)
        self.es_query_builder = ESQueryBuilder(self.agent.es, settings.es_index, self.llm)
        self.state = AgentState()
        self.schedule_input = schedule_input.resolve() if schedule_input else None
        self.settings.outputs_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        print("视频业务「一、整体情况」持续查询智能体已启动。")
        print("输入普通问题不会生成文档；只有输入 /report 才生成报告。输入 /help 查看示例，输入 /exit 退出。")
        print(f"报告输出目录：{self.settings.outputs_dir.resolve()}")
        if self.schedule_input:
            print(f"赛事日赛程文件：{self.schedule_input}")
        if not self.llm.enabled:
            print("提示：未配置 LLM_API_KEY/DEEPSEEK_API_KEY，智能数据查询和普通大模型回复不可用；仍可使用 /report。")

        while True:
            try:
                question = _normalize_input_text(input("\n请输入问题 > ").strip()).strip()
            except (EOFError, KeyboardInterrupt):
                print("\n已退出。")
                return

            if not question:
                print("问题不能为空。")
                continue
            
            if self._handle_command(question):
                continue

            self._handle_question(question)

    def _handle_command(self, input_text: str) -> bool:
        stripped = _normalize_input_text(input_text).strip()
        command = stripped.lower()
        if command in {"/exit", "/quit", "/q", "exit", "quit", "q", "退出"}:
            print("已退出。")
            raise SystemExit(0)
        if command in {"/help", "help", "帮助"}:
            print(HELP_TEXT)
            return True
        if command in {"/context", "context", "上下文"}:
            self._print_context()
            return True
        if command == "/report" or command.startswith("/report "):
            self._handle_report_command(stripped)
            return True
        if stripped.startswith("/生成报告"):
            print("生成文档请使用 /report。普通输入不会生成文档。")
            return True
        if stripped.startswith("/"):
            print("未知命令。输入 /help 查看可用命令。")
            return True
        return False

    def _handle_question(self, question: str) -> None:
        errors = _validate_chat_question(question)
        if errors:
            print("输入校验未通过：" + "；".join(errors))
            return

        self.state.add_user(question)
        logger.info("User query: %s", question)

        try:
            history_answer = self._handle_history_question(question)
            if history_answer is not None:
                answer = history_answer
            elif self._should_query_data(question):
                answer = self._handle_data_query(question)
            else:
                answer = self._answer_normally(question)
            answer = _sanitize_console_text(answer)
            self.state.add_assistant(answer)
            self._maybe_compact_history()
            print(answer)
        except LLMUnavailableError as exc:
            message = _sanitize_console_text(f"{exc} 如需生成报告，请使用 /report。")
            self.state.add_assistant(message)
            self._maybe_compact_history()
            print(message)
        except ESQueryError as exc:
            message = _sanitize_console_text(f"数据查询失败：{exc}")
            self.state.add_assistant(message)
            self._maybe_compact_history()
            print(message)
        except Exception as exc:
            logger.exception("Failed to handle user question")
            message = _sanitize_console_text(f"处理失败：{exc}")
            self.state.add_assistant(message)
            self._maybe_compact_history()
            print(message)

    def _handle_report_command(self, input_text: str) -> None:
        dates = self._extract_dates(input_text)
        start_date = dates[0] if dates else self.state.last_start_date
        end_date = dates[1] if len(dates) > 1 else (dates[0] if dates else self.state.last_end_date)
        plan = QueryPlan(
            question="生成整体情况报告",
            start_date=start_date,
            end_date=end_date,
            section_focus="full",
            note=(
                f"使用 /report 命令指定日期范围：{start_date or '未限定'} 至 {end_date or '未限定'}。"
                if dates
                else "使用 /report 命令生成完整整体情况报告；未指定日期则查询全量数据。"
            ),
        )
        try:
            output_path = make_report_path(self.settings.outputs_dir, "整体情况报告")
            report_path = self._generate_with_retry(plan, output_path)
            self.state.remember_report(report_path, plan.start_date, plan.end_date)
            markdown_path = report_path.with_suffix(".md")
            answer = f"报告已生成：\nHTML：{report_path.resolve()}\nMarkdown：{markdown_path.resolve()}"
            self.state.add_assistant(answer)
            print(answer)
        except Exception as exc:
            logger.exception("Failed to generate report")
            message = f"生成失败：{exc}"
            self.state.add_assistant(message)
            print(message)

    def _extract_dates(self, input_text: str) -> list[str]:
        dates = []
        for match in DATE_PATTERN.finditer(input_text):
            year, month, day = match.groups()
            dates.append(f"{int(year):04d}-{int(month):02d}-{int(day):02d}")
        return dates

    def _should_query_data(self, question: str) -> bool:
        lower = question.lower()
        if _is_report_request_text(question):
            return False
        if any(term in lower for term in NORMAL_CHAT_TERMS):
            return False
        if self.state.last_query_result_summary and any(term in question for term in CONTEXT_QUERY_TERMS):
            if not self._is_history_meta_question(question):
                return True
        if any(term in question for term in DATA_QUERY_TERMS):
            return True
        if not self.llm.enabled:
            return False

        response = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是意图路由器，只输出 JSON：{\"needs_data_query\": true/false}。\n\n"
                        "needs_data_query = true 的情况：\n"
                        "- 用户要查询、统计、筛选、分析 ES 中的工单/投诉/标签数据\n"
                        "- 用户引用上一条数据查询的结果或聚合（如「刚才的最高项」、「上一个查询的峰值」）\n"
                        "- 用户要求验证/补充上一条数据查询\n\n"
                        "needs_data_query = false 的情况：\n"
                        "- 纯闲聊、问候、介绍自己\n"
                        "- 询问对话历史本身（如「上一个问题问了你什么」、「一开始我问了什么」）\n"
                        "- 询问使用方法和帮助\n"
                        "- 解释概念、写作、翻译等非数据任务\n\n"
                        "注意：如果用户问的是「上一个问题是什么」（关于对话历史），而不是「上一个查询的最高项是什么」（关于数据），应输出 false。"
                    ),
                },
                *self._context_messages(exclude_current=True, include_query_context=True, limit=6),
                {"role": "user", "content": question},
            ],
            temperature=0.0,
        )
        parsed = parse_json_object(response.content)
        return bool(parsed and parsed.get("needs_data_query") is True)

    def _handle_data_query(self, question: str) -> str:
        history = self._context_messages(exclude_current=True, include_query_context=True, limit=8)
        intent = self.es_query_builder.generate_intent(
            question,
            history=history,
            last_query_summary=self.state.last_query_result_summary,
            last_query_dsl=self.state.last_query_dsl,
        )
        logger.info("ES query plan: %s", intent.get("explanation"))
        results = self.es_query_builder.execute_intent(intent)
        parsed_results = self.es_query_builder.parse_results(results, intent)
        result_summary = self.es_query_builder.summarize_results(parsed_results)
        answer = self.es_query_builder.analyze_results(
            question,
            parsed_results,
            intent,
            result_summary=result_summary,
            history=history,
        )
        self.state.remember_query(question, intent, intent["query"], result_summary, answer)
        return answer

    def _answer_normally(self, question: str) -> str:
        if _is_report_request_text(question):
            return "普通输入不会生成文档。如需生成完整“一、整体情况”报告，请输入 /report。"
        if any(term in question.lower() for term in NORMAL_CHAT_TERMS):
            return (
                "我可以做三类事：\n"
                "1. 回答使用方式和能力说明等普通问题，不生成文档。\n"
                "2. 对工单、投诉、标签、趋势、情绪、省份等数据问题生成只读 ES 查询，并基于查询结果回答。\n"
                "3. 只有在你输入 /report 时，才生成完整“一、整体情况”报告文档。"
            )
        if not self.llm.enabled:
            return "这是普通问题，不会生成文档。当前未配置大模型 API Key，因此只能回答固定帮助；数据查询和普通大模型回复暂不可用。"

        response = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是本地工单分析助手。正常回答用户的非数据查询问题。"
                        "不要声称已查询 Elasticsearch，不要生成或保存任何报告文件。"
                        "如用户想生成报告，提醒其使用 /report。"
                        "如果用户继续追问上文的数据查询，请说明该问题应走数据查询路径，而不是编造数据。"
                    ),
                },
                *self._context_messages(exclude_current=True, include_query_context=False, limit=8),
                {"role": "user", "content": question},
            ],
            temperature=0.2,
        )
        if response.used_fallback or not response.content.strip():
            return "这是普通问题，不会生成文档。如需生成报告，请输入 /report。"
        return response.content.strip()

    def _is_history_meta_question(self, question: str) -> bool:
        return any(pattern.search(question) for pattern in HISTORY_QUERY_PATTERNS)

    def _handle_history_question(self, question: str) -> str | None:
        question_lower = question.lower()

        if re.search(r"上一个问题|上一条问题|上一轮|刚才.*问|之前.*问|之前.*说|刚刚.*问", question_lower):
            prev = self.state.get_previous_user_question_before_current()
            if prev:
                return f"您上一个问题是：「{prev}」"
            return "这是本轮对话的第一个问题，没有上一个问题。"

        if re.search(r"一开始|最开始|最早.*问|第一个问题", question_lower):
            first = self.state.get_first_user_question()
            if first:
                return f"您最开始问的问题是：「{first}」"
            return "暂无对话历史记录。"

        match = re.search(r"第([一二三四五六七八九十\d]+).*(问题|轮|次)", question_lower)
        if match:
            idx = _chinese_to_int(match.group(1))
            if idx <= 0:
                return "轮次编号无效。"
            q = self.state.get_user_question_at(idx - 1)
            if q:
                return f"第 {idx} 个问题是：「{q}」"
            total = self.state.user_question_count()
            return f"第 {idx} 个问题不存在，当前共 {total} 个问题。"

        if re.search(r"刚才聊了什么|之前聊了什么|聊了什么", question_lower):
            questions = self.state.get_user_questions()
            if not questions:
                return "暂无对话历史记录。"
            lines = [f"我们共聊了 {len(questions)} 轮，话题如下："]
            for i, q in enumerate(questions, 1):
                lines.append(f"  {i}. {q[:80]}")
            return "\n".join(lines)

        return None

    def _context_messages(
        self,
        exclude_current: bool = False,
        include_query_context: bool = False,
        limit: int = 8,
    ) -> list[dict[str, str]]:
        messages = self.state.history_for_llm(limit=limit)
        if exclude_current and messages and messages[-1]["role"] == "user":
            messages = messages[:-1]
        if include_query_context and self.state.last_query_result_summary:
            payload = {
                "last_query_question": self.state.last_query_question,
                "last_query_explanation": (self.state.last_query_intent or {}).get("explanation"),
                "last_query_dsl": self.state.last_query_dsl,
                "last_query_result_summary": self.state.last_query_result_summary,
                "last_query_answer": self.state.last_query_answer,
            }
            messages.append(
                {
                    "role": "system",
                    "content": "最近一次已执行的 Elasticsearch 查询上下文：" + json.dumps(payload, ensure_ascii=False)[:6000],
                }
            )
        return messages

    def _maybe_compact_history(self) -> None:
        keep_recent = 8
        if len(self.state.turns) <= 14:
            return

        older_turns = self.state.turns[:-keep_recent]
        recent_turns = self.state.turns[-keep_recent:]

        key_moments = []
        for turn in older_turns:
            if turn.role == "user":
                key_moments.append(f"[用户]: {turn.content[:200]}")
            else:
                content = turn.content[:300]
                if any(kw in content for kw in ["峰值", "占比", "结论", "总计"]):
                    key_moments.append(f"[结论]: {content}")

        if not self.llm.enabled:
            fallback_summary = "；".join(key_moments[-6:])
            if fallback_summary.strip():
                self.state.summary = fallback_summary[:1200]
            self.state.turns = recent_turns
            return

        payload = {
            "previous_summary": self.state.summary,
            "older_turns": [
                {"role": turn.role, "content": turn.content, "created_at": turn.created_at}
                for turn in older_turns
            ],
        }
        response = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是会话上下文压缩器。用中文在 800 字以内总结对后续有用的信息："
                        "用户目标、已查询的数据主题、关键数字/标签/日期、未解决追问。"
                        "特别注意保留用户的核心诉求和重要数据发现。"
                        "不要加入不存在的信息。只输出摘要文本。"
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.1,
        )
        if response.content.strip() and not response.used_fallback:
            self.state.summary = response.content.strip()[:1200]
        else:
            fallback_summary = "；".join(key_moments[-6:])
            if fallback_summary.strip():
                self.state.summary = fallback_summary[:1200]
        self.state.turns = recent_turns

    def _generate_with_retry(self, plan: QueryPlan, output_path: Path) -> Path:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                query_context = {
                    "question": plan.question,
                    "start_date": plan.start_date,
                    "end_date": plan.end_date,
                    "focus": plan.focus,
                    "section_focus": plan.section_focus,
                    "note": plan.note,
                    "used_llm": plan.used_llm,
                }
                return self.agent.generate_report(
                    output_path=output_path,
                    start_date=plan.start_date,
                    end_date=plan.end_date,
                    query_context=query_context,
                    schedule_input=self.schedule_input,
                )
            except Exception as exc:
                last_error = exc
                logger.warning("Report generation attempt %s failed: %s", attempt + 1, exc)
        raise RuntimeError(f"重试后仍无法生成报告：{last_error}")

    def _print_context(self) -> None:
        print("=== 会话状态 ===")
        print(f"最近报告：{self.state.last_report_path.resolve() if self.state.last_report_path else '暂无'}")
        print(f"最近日期范围：{self.state.last_start_date or '未限定'} 至 {self.state.last_end_date or '未限定'}")
        print(f"累计生成报告数：{len(self.state.generated_reports)}")
        print()
        print("=== 对话历史 ===")
        questions = self.state.get_user_questions()
        print(f"当前共 {len(questions)} 个用户问题")
        if questions:
            print("用户问题列表：")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q[:80]}{'...' if len(q) > 80 else ''}")
        print()
        print(f"会话摘要：{self.state.summary or '暂无'}")
        print(f"最近数据查询：{self.state.last_query_question or '暂无'}")
