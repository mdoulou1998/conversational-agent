"""Validate tool call before it is executed by the agent.

Schema-check every call, then gate destructive ones on order ownership,
refund cap, and order total. A refund the model invented for someone
else's order is rejected here and never reaches execution.
"""

from __future__ import annotations

from support_agent.config import REFUND_CAP
from support_agent.domain import ToolCall, ValidationResult
from support_agent.session import Session
from support_agent.tools.fixtures import ORDERS
from support_agent.tools.registry import ToolRegistry


def validate_tool_call(
    call: ToolCall, session: Session, registry: ToolRegistry
) -> ValidationResult:
    tool = registry.tools.get(call.name)
    if tool is None:
        return ValidationResult(valid=False, reason=f"unknown tool '{call.name}'")

    required = tool.parameters.get("required", [])
    missing = [arg for arg in required if arg not in call.arguments]
    if missing:
        return ValidationResult(valid=False, reason=f"missing required arguments: {missing}")

    if not tool.destructive:
        return ValidationResult(valid=True, normalized_args=call.arguments)

    if call.name == "issue_refund":
        return _validate_refund(call, session)
    if call.name == "reset_password":
        return _validate_reset_password(call, session)

    return ValidationResult(valid=True, normalized_args=call.arguments)


def _validate_refund(call: ToolCall, session: Session) -> ValidationResult:
    order_id = call.arguments.get("order_id")
    amount = call.arguments.get("amount")

    if not isinstance(order_id, str):
        return ValidationResult(valid=False, reason="order_id must be a string")

    order = ORDERS.get(order_id)
    if order is None:
        return ValidationResult(valid=False, reason=f"order '{order_id}' does not exist")
    if order.customer_id != session.customer_id:
        return ValidationResult(valid=False, reason="order does not belong to this customer")
    if not isinstance(amount, (int, float)) or amount <= 0:
        return ValidationResult(valid=False, reason="refund amount must be a positive number")
    if amount > order.total:
        return ValidationResult(valid=False, reason="refund amount exceeds the order total")
    if amount > REFUND_CAP:
        return ValidationResult(
            valid=False, reason=f"refund amount exceeds the cap of {REFUND_CAP}"
        )

    return ValidationResult(valid=True, normalized_args=call.arguments)


def _validate_reset_password(call: ToolCall, session: Session) -> ValidationResult:
    if call.arguments.get("customer_id") != session.customer_id:
        return ValidationResult(
            valid=False, reason="cannot reset a password for a different customer"
        )
    return ValidationResult(valid=True, normalized_args=call.arguments)
