from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from support_agent.domain import Message, ToolCall


@dataclass
class LLMDecision:
    """What the model decided to do this step: call a tool, or answer.

    Exactly one of these is meaningfully set. `tool_call is None` is what the
    loop reads as "the model is done, use final_message."
    """

    tool_call: ToolCall | None = None
    final_message: str | None = None


class LLMClient(Protocol):
    """The one seam every model implementation sits behind. Swap Gemini for
    FakeLLM, or later a different provider, without touching the loop."""

    def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> LLMDecision: ...
