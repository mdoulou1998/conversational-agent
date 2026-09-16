"""The agent loop: decide -> validate -> execute -> observe.

Every exit is an AgentOutcome carrying a StopReason. Nothing here raises to
end a run - an unknown tool, a bad arg, a blocked destructive call, a
repeated call, and running out of steps are all handled outcomes, not
exceptions.
"""

from __future__ import annotations

import logging

from support_agent.domain import AgentOutcome, StopReason, ToolCall, ToolResult
from support_agent.llm.base import LLMClient
from support_agent.session import Session
from support_agent.tools.registry import ToolRegistry
from support_agent.validate.validation import validate_tool_call

logger = logging.getLogger(__name__)


class AgentLoop:
    def __init__(self, llm: LLMClient, registry: ToolRegistry) -> None:
        self.llm = llm
        self.registry = registry

    def run(self, session: Session, user_message: str) -> AgentOutcome:
        logger.info("loop.start customer_id=%s message=%r", session.customer_id, user_message)
        self._seed_identity(session)
        session.add_user_message(user_message)
        tool_results: list[ToolResult] = []
        try:
            for step in range(1, session.max_steps + 1):
                decision = self.llm.complete(session.messages, self.registry.schema())

                if decision.tool_call is None:
                    final_message = decision.final_message or ""
                    session.add_assistant_message(final_message)
                    logger.info("loop.resolved step=%d message=%r", step, final_message)
                    return AgentOutcome(
                        stop_reason=StopReason.RESOLVED,
                        final_message=final_message,
                        tool_results=tool_results,
                        steps_taken=step,
                    )

                logger.info(
                    "loop.decide step=%d tool=%s args=%s",
                    step,
                    decision.tool_call.name,
                    decision.tool_call.arguments,
                )
                outcome = self._handle_tool_call(session, decision.tool_call, step, tool_results)
                if outcome is not None:
                    logger.info(
                        "loop.stop step=%d reason=%s message=%r",
                        step,
                        outcome.stop_reason.value,
                        outcome.final_message,
                    )
                    return outcome

            logger.warning("loop.step_limit steps=%d", session.max_steps)
            return AgentOutcome(
                stop_reason=StopReason.STEP_LIMIT,
                final_message="Reached the maximum number of steps without resolving.",
                tool_results=tool_results,
                steps_taken=session.max_steps,
            )
        except Exception as e:
            logger.exception("loop.exception: %s", e)
            return AgentOutcome(
                stop_reason=StopReason.EXCEPTION,
                final_message=f"An unexpected error occurred: {e}",
                tool_results=tool_results,
                steps_taken=len(tool_results),
            )

    def _handle_tool_call(
        self, session: Session, call: ToolCall, step: int, tool_results: list[ToolResult]
    ) -> AgentOutcome | None:
        """Decide -> validate -> execute -> observe. Returns an AgentOutcome if the run should stop, else None."""
        validation = validate_tool_call(call, session, self.registry)
        logger.info("loop.validate step=%d tool=%s valid=%s", step, call.name, validation.valid)
        if not validation.valid:
            logger.warning(
                "loop.policy_block step=%d tool=%s reason=%s", step, call.name, validation.reason
            )
            return AgentOutcome(
                stop_reason=StopReason.POLICY_BLOCK,
                final_message=validation.reason or "tool call rejected",
                tool_results=tool_results,
                steps_taken=step,
            )

        if self._is_repeat(session, call):
            logger.warning("loop.repeat_detected step=%d tool=%s", step, call.name)
            return AgentOutcome(
                stop_reason=StopReason.LOOP_DETECTED,
                final_message="Detected a repeated tool call with identical arguments; "
                "stopping rather than spinning.",
                tool_results=tool_results,
                steps_taken=step,
            )

        validated_call = ToolCall(
            name=call.name,
            arguments=validation.normalized_args or call.arguments,
            call_id=call.call_id,
        )
        result = self.registry.execute(validated_call)
        session.add_tool_result(result)
        tool_results.append(result)
        logger.info(
            "loop.execute step=%d tool=%s valid=%s escalated=%s",
            step,
            result.tool_name,
            result.valid,
            result.escalated,
        )

        if result.escalated:
            return AgentOutcome(
                stop_reason=StopReason.ESCALATED,
                final_message="Escalated to a human.",
                tool_results=tool_results,
                steps_taken=step,
            )

        return None

    def _is_repeat(self, session: Session, call: ToolCall) -> bool:
        """Flags identical tool + args seen before in this session as a loop,
        not progress, so the run can stop instead of spinning on a model
        that keeps retrying the same failed or already-satisfied call."""
        signature = (call.name, tuple(sorted(call.arguments.items())))
        if signature in session.repeated_call_guard:
            return True
        session.repeated_call_guard.append(signature)
        return False

    def _seed_identity(self, session: Session) -> None:
        """Puts the authenticated customer_id in front of the model on the
        first turn of a session, so it can act on this customer without
        asking them to restate who they are, and can ground a lookup call
        against a real identity rather than trusting free text."""
        if session.messages or not session.customer_id:
            return
        session.add_tool_message(
            f"Authenticated session for customer_id={session.customer_id}.",
            name="session_context",
        )
