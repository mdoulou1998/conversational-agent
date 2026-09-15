from support_agent.domain import StopReason, ToolCall
from support_agent.llm.base import LLMDecision
from support_agent.llm.fake import FakeLLM
from support_agent.loop import AgentLoop
from support_agent.session import Session
from support_agent.tools.registry import TOOLS, ToolRegistry


def test_reset_password_resolves_end_to_end() -> None:
    """Exercises the full loop against real fixtures and real validation:
    decide (tool call) -> validate (passes, cust-1 resetting their own
    password) -> execute (the real reset_password stub, against real
    fixture data) -> observe (result lands in session history) -> decide
    again (final message) -> resolved."""
    script = [
        LLMDecision(tool_call=ToolCall(name="reset_password", arguments={"customer_id": "cust-1"})),
        LLMDecision(final_message="A password reset has been sent to the email on account."),
    ]
    loop = AgentLoop(llm=FakeLLM(script), registry=ToolRegistry(TOOLS))
    session = Session(customer_id="cust-1")

    outcome = loop.run(session, "I need to reset my password.")

    assert outcome.stop_reason == StopReason.RESOLVED
    assert outcome.final_message == "A password reset has been sent to the email on account."
    assert outcome.steps_taken == 2

    # the tool's real result made it into session history (the "observe" step)
    assert any("reset_email_sent" in message.content for message in session.messages)
