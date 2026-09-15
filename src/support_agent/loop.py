"""The agent loop: decide -> validate -> execute -> observe.

Every exit is an AgentOutcome carrying a StopReason. Nothing here raises to
end a run — an unknown tool, a bad arg, a blocked destructive call, a
repeated call, and running out of steps are all handled outcomes, not
exceptions.
"""

from __future__ import annotations

from support_agent.config import MAX_STEPS
from support_agent.domain import AgentOutcome, StopReason, ToolCall
from support_agent.llm.base import LLMClient
from support_agent.session import Session
from support_agent.tools.registry import ToolRegistry
from support_agent.validate.validation import validate_tool_call


class AgentLoop:
    def __init__(self, llm: LLMClient, registry: ToolRegistry) -> None:
        self.llm = llm
        self.registry = registry

    def run(self, session: Session, user_message: str) -> AgentOutcome:
        session.add_user_message(user_message)

        for step in range(1, session.max_steps + 1):
            decision = self.llm.complete(session.messages, self.registry.schema())

            if decision.tool_call is None:
                final_message = decision.final_message or ""
                session.add_assistant_message(final_message)
                return AgentOutcome(
                    stop_reason=StopReason.RESOLVED, final_message=final_message, steps_taken=step
                )

            outcome = self._handle_tool_call(session, decision.tool_call, step)
            if outcome is not None:
                return outcome

        return AgentOutcome(
            stop_reason=StopReason.STEP_LIMIT,
            final_message="Reached the maximum number of steps without resolving.",
            steps_taken=MAX_STEPS,
        )

    def _handle_tool_call(self, session: Session, call: ToolCall, step: int) -> AgentOutcome | None:
        validation = validate_tool_call(call, session, self.registry)
        if not validation.valid:
            return AgentOutcome(
                stop_reason=StopReason.POLICY_BLOCK,
                final_message=validation.reason or "tool call rejected",
                steps_taken=step,
            )

        if self._is_repeat(session, call):
            return AgentOutcome(
                stop_reason=StopReason.LOOP_DETECTED,
                final_message="Detected a repeated tool call with identical arguments; "
                "stopping rather than spinning.",
                steps_taken=step,
            )

        validated_call = ToolCall(
            name=call.name,
            arguments=validation.normalized_args or call.arguments,
            call_id=call.call_id,
        )
        result = self.registry.execute(validated_call)
        session.add_tool_result(result)

        if result.escalated:
            return AgentOutcome(
                stop_reason=StopReason.ESCALATED,
                final_message="Escalated to a human.",
                tool_results=[result],
                steps_taken=step,
            )

        return None

    def _is_repeat(self, session: Session, call: ToolCall) -> bool:
        signature = (call.name, tuple(sorted(call.arguments.items())))
        if signature in session.repeated_call_guard:
            return True
        session.repeated_call_guard.append(signature)
        return False
