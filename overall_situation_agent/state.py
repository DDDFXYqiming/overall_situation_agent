from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ConversationTurn:
    role: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class AgentState:
    turns: list[ConversationTurn] = field(default_factory=list)
    summary: str = ""
    first_question: str | None = None
    last_start_date: str | None = None
    last_end_date: str | None = None
    last_report_path: Path | None = None
    generated_reports: list[Path] = field(default_factory=list)
    last_query_question: str | None = None
    last_query_intent: dict[str, Any] | None = None
    last_query_dsl: dict[str, Any] | None = None
    last_query_result_summary: dict[str, Any] | None = None
    last_query_answer: str | None = None

    def add_user(self, content: str) -> None:
        if not self.first_question:
            self.first_question = content
        self.turns.append(ConversationTurn(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        self.turns.append(ConversationTurn(role="assistant", content=content))

    def compact_history(self, limit: int = 8) -> list[dict[str, str]]:
        return [{"role": turn.role, "content": turn.content} for turn in self.turns[-limit:]]

    def history_for_llm(self, limit: int = 8) -> list[dict[str, str]]:
        messages = []
        if self.summary.strip():
            messages.append({"role": "system", "content": f"本轮会话摘要：{self.summary.strip()}"})
        messages.extend(self.compact_history(limit=limit))
        return messages

    def get_previous_user_question(self) -> str | None:
        for turn in reversed(self.turns):
            if turn.role == "user":
                return turn.content
        return None

    def get_previous_user_question_before_current(self) -> str | None:
        found_current = False
        for turn in reversed(self.turns):
            if turn.role == "user":
                if not found_current:
                    found_current = True
                    continue
                return turn.content
        return None

    def get_first_user_question(self) -> str | None:
        return self.first_question

    def get_user_question_at(self, index: int) -> str | None:
        count = 0
        for turn in self.turns:
            if turn.role == "user":
                if count == index:
                    return turn.content
                count += 1
        return None

    def user_question_count(self) -> int:
        return sum(1 for turn in self.turns if turn.role == "user")

    def get_user_questions(self) -> list[str]:
        return [turn.content for turn in self.turns if turn.role == "user"]

    def remember_query(
        self,
        question: str,
        intent: dict[str, Any],
        query_dsl: dict[str, Any],
        result_summary: dict[str, Any],
        answer: str,
    ) -> None:
        self.last_query_question = question
        self.last_query_intent = intent
        self.last_query_dsl = query_dsl
        self.last_query_result_summary = result_summary
        self.last_query_answer = answer

    def remember_report(self, path: Path, start_date: str | None, end_date: str | None) -> None:
        self.last_report_path = path
        self.generated_reports.append(path)
        self.last_start_date = start_date
        self.last_end_date = end_date
