"""Composition root: construct the real dependencies and run one turn."""

from __future__ import annotations

from support_agent.llm.gemini import GeminiClient
from support_agent.loop import AgentLoop
from support_agent.session import Session
from support_agent.tools.registry import TOOLS, ToolRegistry


def main() -> None:
    registry = ToolRegistry(TOOLS)
    llm = GeminiClient()
    loop = AgentLoop(llm=llm, registry=registry)
    session = Session(customer_id="cust-1")

    outcome = loop.run(session, "I need to reset my password.")
    print(outcome)


if __name__ == "__main__":
    main()
