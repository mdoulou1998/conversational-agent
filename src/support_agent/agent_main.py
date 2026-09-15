from __future__ import annotations

from typing import Any, Protocol

from support_agent.llm.gemini import GeminiClient
from support_agent.schemas.domain import (
    AgentOutcome,
    Message,
    StopReason,
    ToolCall,
    ValidationResult,
)
from support_agent.schemas.session import Session
from support_agent.tools.registry import TOOLS, ToolRegistry


class LLMClient(Protocol):
    def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> dict[str, Any]: ...


class PolicyValidator:
    def validate_tool_call(self, call: ToolCall) -> ValidationResult:
        return ValidationResult(ok=True, normalized_args=call.arguments)


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
