from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from support_agent.schemas.domain import Message, ToolResult


@dataclass
class Session:
    """
    Represents a support agent session, maintaining the state of the conversation and customer information."""
    customer_id: str | None = None
    messages: list[Message] = field(default_factory=list)
    max_steps: int = 6
    token_budget: int = 2000
    repeated_call_guard: list[tuple[str, tuple[tuple[str, Any], ...]]] = field(default_factory=list)

    def set_customer_id(self, customer_id: str) -> None:
        """
        Sets the customer ID for the session. Raises a ValueError if the provided customer_id is empty or only whitespace.
        """
        if not customer_id or not customer_id.strip():
            raise ValueError("customer_id cannot be empty")
        self.customer_id = customer_id.strip()

    def add_user_message(self, text: str) -> None:
        """
        Adds a user message to the session. Raises a ValueError if the provided text is empty or only whitespace.
        """
        self.messages.append(Message(role="user", content=text))

    def add_assistant_message(self, text: str) -> None:
        """
        Adds an assistant message to the session. Raises a ValueError if the provided text is empty or only whitespace.
        """
        self.messages.append(Message(role="assistant", content=text))

    def add_tool_message(self, text: str, name: str | None = None) -> None:
        """
        Adds a tool message to the session. Raises a ValueError if the provided text is empty or only whitespace.
        """
        self.messages.append(Message(role="tool", content=text, name=name))

    def add_tool_result(self, result: ToolResult) -> None:
        """
        Adds a tool result to the session as a tool message.
        """
        self.add_tool_message(str(result.result or result.error or result.tool_name), name=result.tool_name)

    def add_system_message(self, text: str) -> None:
        """
        Adds a system message to the session. Raises a ValueError if the provided text is empty or only whitespace.
        """
        self.messages.append(Message(role="system", content=text))
