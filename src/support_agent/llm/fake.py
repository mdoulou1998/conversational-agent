from __future__ import annotations

from typing import Any

from support_agent.domain import Message
from support_agent.llm.base import LLMDecision


class FakeLLM:
    """Scripted, deterministic LLMClient. Plays back a fixed sequence of
    decisions on successive calls, so tests and the eval harness are
    reproducible and free of real model calls."""

    def __init__(self, script: list[LLMDecision]) -> None:
        self._script = list(script)
        self._calls = 0

    def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> LLMDecision:
        if self._calls >= len(self._script):
            return LLMDecision(final_message="I'm not sure how to help further.")
        decision = self._script[self._calls]
        self._calls += 1
        return decision
