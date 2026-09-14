from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class StopReason(str, Enum):
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    STEP_LIMIT = "step_limit"
    BUDGET_EXHAUSTED = "budget_exhausted"
    POLICY_BLOCK = "policy_block"


@dataclass
class Message:
    role: Literal["user", "assistant", "tool", "system"]
    content: str
    name: str | None = None

    def __post_init__(self) -> None:
        valid_roles = {"user", "assistant", "tool", "system"}
        if self.role not in valid_roles:
            raise ValueError(f"Invalid message role: {self.role}")

        if not isinstance(self.content, str):
            raise TypeError("Message content must be a string")

        cleaned = self.content.strip()
        if not cleaned:
            raise ValueError("Message content cannot be empty")

        self.content = cleaned


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str | None = None


@dataclass
class ToolResult:
    tool_name: str
    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    is_final: bool = False
    escalated: bool = False


@dataclass
class ValidationResult:
    ok: bool
    reason: str | None = None
    normalized_args: dict[str, Any] | None = None


@dataclass
class AgentOutcome:
    stop_reason: StopReason
    final_message: str | None = None
    tool_results: list[ToolResult] = field(default_factory=list)
    steps_taken: int = 0
    token_usage: int = 0