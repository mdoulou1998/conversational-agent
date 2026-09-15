"""Minimal agent loop: decide -> validate -> execute, terminating sensibly.

Everything the loop needs lives in this one file on purpose. Read top to
bottom: types, stub tools, a stubbed LLM, validation, then the loop itself.
No provider SDK, no registry indirection, no config module to jump to.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

MAX_STEPS = 6
REFUND_CAP = 50.0


class StopReason(str, Enum):
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    STEP_LIMIT = "step_limit"
    POLICY_BLOCK = "policy_block"


@dataclass
class Message:
    role: str  # "user" | "assistant" | "tool"
    content: str


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class Decision:
    """What the model decided to do this step: call a tool, or answer."""

    tool_call: ToolCall | None = None
    final_message: str | None = None


@dataclass
class Outcome:
    stop_reason: StopReason
    final_message: str
    steps_taken: int = 0


# --- stub data, standing in for real account/order systems ------------------

_CUSTOMERS: dict[str, dict[str, Any]] = {
    "12345": {"order_ids": ["order-1", "order-2"], "email": "amelia@example.com"},
}
_ORDERS: dict[str, dict[str, Any]] = {
    "order-1": {"customer_id": "12345", "total": 49.99},
    "order-2": {"customer_id": "12345", "total": 19.99},
}


# --- stub tools --------------------------------------------------------------


def kb_search(query: str) -> dict[str, Any]:
    return {"chunks": [f"Knowledge base result for: {query}"]}


def account_lookup(customer_id: str) -> dict[str, Any]:
    account = _CUSTOMERS.get(customer_id)
    if account is None:
        return {"error": f"unknown customer '{customer_id}'"}
    return account


def issue_refund(order_id: str, amount: float) -> dict[str, Any]:
    return {"status": "refunded", "order_id": order_id, "amount": amount}


def reset_password(customer_id: str) -> dict[str, Any]:
    return {"status": "A password reset has been sent to the email on account."}


def create_ticket(summary: str, priority: str) -> dict[str, Any]:
    return {"status": "ticket created", "priority": priority}


def escalate_to_human(reason: str) -> dict[str, Any]:
    return {"status": "escalated", "reason": reason}


TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "kb_search": kb_search,
    "account_lookup": account_lookup,
    "issue_refund": issue_refund,
    "reset_password": reset_password,
    "create_ticket": create_ticket,
    "escalate_to_human": escalate_to_human,
}

DESTRUCTIVE_TOOLS = {"issue_refund", "reset_password"}


# --- stubbed LLM: scripted and deterministic ---------------------------------


class StubLLM:
    """Plays back a fixed sequence of decisions. Swap this class for a real
    model later; nothing else in this file needs to change."""

    def __init__(self, script: list[Decision]) -> None:
        self._script = script
        self._step = 0

    def decide(self, history: list[Message]) -> Decision:
        if self._step >= len(self._script):
            return Decision(final_message="I'm not sure how to help with that.")
        decision = self._script[self._step]
        self._step += 1
        return decision


# --- validate: the untrusted-input seam --------------------------------------


def validate(call: ToolCall, customer_id: str) -> tuple[bool, str | None]:
    """Schema/tool-name check for every call; ownership, cap, and total
    checks for destructive ones. A refund the model invented never reaches
    `execute`."""
    if call.name not in TOOLS:
        return False, f"unknown tool '{call.name}'"

    if call.name not in DESTRUCTIVE_TOOLS:
        return True, None

    if call.name == "issue_refund":
        order = _ORDERS.get(call.arguments.get("order_id"))
        if order is None:
            return False, "order does not exist"
        if order["customer_id"] != customer_id:
            return False, "order does not belong to this customer"
        amount = call.arguments.get("amount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            return False, "refund amount must be a positive number"
        if amount > order["total"]:
            return False, "refund amount exceeds the order total"
        if amount > REFUND_CAP:
            return False, f"refund amount exceeds the cap of {REFUND_CAP}"
        return True, None

    if call.name == "reset_password":
        if call.arguments.get("customer_id") != customer_id:
            return False, "cannot reset a password for a different customer"
        return True, None

    return True, None


# --- the loop: decide -> validate -> execute ---------------------------------


def run(llm: StubLLM, customer_id: str, message: str) -> Outcome:
    history = [Message("user", message)]

    for step in range(1, MAX_STEPS + 1):
        decision = llm.decide(history)

        if decision.tool_call is None:
            return Outcome(StopReason.RESOLVED, decision.final_message or "", steps_taken=step)

        ok, reason = validate(decision.tool_call, customer_id)
        if not ok:
            return Outcome(
                StopReason.POLICY_BLOCK, reason or "tool call rejected", steps_taken=step
            )

        result = TOOLS[decision.tool_call.name](**decision.tool_call.arguments)
        history.append(Message("tool", str(result)))

        if decision.tool_call.name == "escalate_to_human":
            return Outcome(StopReason.ESCALATED, "Escalated to a human.", steps_taken=step)

    return Outcome(
        StopReason.STEP_LIMIT, "Reached the step limit without resolving.", steps_taken=MAX_STEPS
    )


if __name__ == "__main__":
    script = [
        Decision(tool_call=ToolCall("reset_password", {"customer_id": "12345"})),
        Decision(final_message="A password reset has been sent to the email on account."),
    ]
    outcome = run(StubLLM(script), customer_id="12345", message="I need to reset my password.")
    print(outcome)
