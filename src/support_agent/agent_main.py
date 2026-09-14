from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from support_agent.llm.gemini import GeminiClient
from support_agent.schemas.domain import AgentOutcome, Message, StopReason, ToolCall, ToolResult, ValidationResult
from support_agent.schemas.session import Session
from support_agent.tools.account_lookup import account_lookup
from support_agent.tools.actions import create_support_ticket, issue_refund, reset_password
from support_agent.tools.escalate import escalate_case
from support_agent.tools.kb_search import kb_search


class LLMClient(Protocol):
    def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> dict[str, Any]:
        ...


class Tool(Protocol):
    name: str
    description: str
    destructive: bool

    def invoke(self, **kwargs: Any) -> ToolResult:
        ...


@dataclass
class FunctionTool:
    """Adapts a plain stub function in tools/ to the Tool protocol."""

    name: str
    description: str
    destructive: bool
    fn: Callable[..., Any]

    def invoke(self, **kwargs: Any) -> ToolResult:
        try:
            result = self.fn(**kwargs)
        except TypeError as exc:
            return ToolResult(tool_name=self.name, ok=False, error=str(exc))
        return ToolResult(tool_name=self.name, ok=True, result=result)


class PolicyValidator:
    def validate_tool_call(self, call: ToolCall) -> ValidationResult:
        return ValidationResult(ok=True, normalized_args=call.arguments)


class ToolRegistry:
    def __init__(self, tools: dict[str, Tool]):
        self.tools = tools

    def schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": {},
            }
            for tool in self.tools.values()
        ]

    def execute(self, call: ToolCall) -> ToolResult:
        tool = self.tools.get(call.name)
        if tool is None:
            return ToolResult(tool_name=call.name, ok=False, error="unknown tool")
        return tool.invoke(**call.arguments)


class AgentLoop:
    def __init__(self, llm: LLMClient, registry: ToolRegistry, validator: PolicyValidator):
        self.llm = llm
        self.registry = registry
        self.validator = validator

    def run(self, session: Session, user_message: str) -> AgentOutcome:
        session.add_user_message(user_message)
        step_count = 0

        while step_count < session.max_steps:
            step_count += 1

            decision = self.llm.complete(
                messages=session.messages,
                tools=self.registry.schema(),
            )

            tool_call = self._extract_tool_call(decision)
            if tool_call is None:
                return AgentOutcome(
                    stop_reason=StopReason.RESOLVED,
                    final_message=decision.get("final_message", ""),
                    steps_taken=step_count,
                )

            validation = self.validator.validate_tool_call(tool_call)
            if not validation.ok:
                return AgentOutcome(
                    stop_reason=StopReason.POLICY_BLOCK,
                    final_message=validation.reason or "tool call rejected",
                    steps_taken=step_count,
                )

            tool_result = self.registry.execute(tool_call)
            session.add_tool_result(tool_result)

            if tool_result.ok and tool_result.is_final:
                return AgentOutcome(
                    stop_reason=StopReason.RESOLVED,
                    final_message=str(tool_result.result),
                    tool_results=[tool_result],
                    steps_taken=step_count,
                )

            if tool_result.escalated:
                return AgentOutcome(
                    stop_reason=StopReason.ESCALATED,
                    final_message="Escalated to a human",
                    tool_results=[tool_result],
                    steps_taken=step_count,
                )

            self._enforce_repeat_guard(session, tool_call)

        return AgentOutcome(
            stop_reason=StopReason.STEP_LIMIT,
            final_message="Agent hit the maximum step limit.",
            steps_taken=step_count,
        )

    def _extract_tool_call(self, decision: dict[str, Any]) -> ToolCall | None:
        tool_name = decision.get("tool_name")
        arguments = decision.get("arguments") or {}
        if not tool_name:
            return None
        return ToolCall(name=str(tool_name), arguments=dict(arguments))

    def _enforce_repeat_guard(self, session: Session, call: ToolCall) -> None:
        signature = (call.name, tuple(sorted(call.arguments.items())))
        if signature in session.repeated_call_guard:
            raise RuntimeError("repeat call guard triggered")
        session.repeated_call_guard.append(signature)


TOOLS: dict[str, Tool] = {
    "lookup_customer_order": FunctionTool(
        name="lookup_customer_order",
        description="Looks up a customer's recent orders, subscription, and usage details.",
        destructive=False,
        fn=account_lookup,
    ),
    "search_kb": FunctionTool(
        name="search_kb",
        description="Searches the product knowledge base and returns the top matching chunks.",
        destructive=False,
        fn=kb_search,
    ),
    "escalate_case": FunctionTool(
        name="escalate_case",
        description="Escalates a support case to a human with a reason.",
        destructive=False,
        fn=escalate_case,
    ),
    "issue_refund": FunctionTool(
        name="issue_refund",
        description="Issues a refund for a given order ID and amount.",
        destructive=True,
        fn=issue_refund,
    ),
    "reset_password": FunctionTool(
        name="reset_password",
        description="Initiates a password reset for a customer.",
        destructive=True,
        fn=reset_password,
    ),
    "create_support_ticket": FunctionTool(
        name="create_support_ticket",
        description="Creates a support ticket for a customer with a summary and priority.",
        destructive=False,
        fn=create_support_ticket,
    ),
}


def main() -> None:
    registry = ToolRegistry(TOOLS)
    validator = PolicyValidator()
    llm = GeminiClient()
    loop = AgentLoop(llm=llm, registry=registry, validator=validator)
    session = Session(customer_id="12345")
    outcome = loop.run(session, "I need to reset my password.")
    print(outcome)


if __name__ == "__main__":
    main()