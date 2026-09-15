from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from support_agent.schemas.domain import ToolCall, ToolResult
from support_agent.tools.account_lookup import account_lookup
from support_agent.tools.actions import create_support_ticket, issue_refund, reset_password
from support_agent.tools.escalate import escalate_case
from support_agent.tools.kb_search import kb_search
from support_agent.tools.schema import tools as TOOL_SCHEMAS

_SCHEMA_BY_NAME = {schema["name"]: schema for schema in TOOL_SCHEMAS}


class Tool(Protocol):
    name: str
    description: str
    destructive: bool
    parameters: dict[str, Any]

    def invoke(self, **kwargs: Any) -> ToolResult: ...


@dataclass
class FunctionTool:
    """Adapts a plain stub function in tools/ to the Tool protocol."""

    name: str
    description: str
    destructive: bool
    parameters: dict[str, Any]
    fn: Callable[..., Any]

    def invoke(self, **kwargs: Any) -> ToolResult:
        try:
            result = self.fn(**kwargs)
        except TypeError as exc:
            return ToolResult(tool_name=self.name, valid=False, error=str(exc))
        return ToolResult(tool_name=self.name, valid=True, result=result)


def _function_tool(name: str, destructive: bool, fn: Callable[..., Any]) -> FunctionTool:
    schema = _SCHEMA_BY_NAME[name]
    return FunctionTool(
        name=name,
        description=schema["description"],
        destructive=destructive,
        parameters=schema["parameters"],
        fn=fn,
    )


TOOLS: dict[str, Tool] = {
    "lookup_customer_order": _function_tool(
        "lookup_customer_order", destructive=False, fn=account_lookup
    ),
    "search_kb": _function_tool("search_kb", destructive=False, fn=kb_search),
    "escalate_case": _function_tool("escalate_case", destructive=False, fn=escalate_case),
    "issue_refund": _function_tool("issue_refund", destructive=True, fn=issue_refund),
    "reset_password": _function_tool("reset_password", destructive=True, fn=reset_password),
    "create_support_ticket": _function_tool(
        "create_support_ticket", destructive=False, fn=create_support_ticket
    ),
}


class ToolRegistry:
    def __init__(self, tools: dict[str, Tool]):
        self.tools = tools

    def schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self.tools.values()
        ]

    def execute(self, call: ToolCall) -> ToolResult:
        tool = self.tools.get(call.name)
        if tool is None:
            return ToolResult(tool_name=call.name, valid=False, error="unknown tool")
        return tool.invoke(**call.arguments)
