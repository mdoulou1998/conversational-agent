from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from support_agent.domain import Message

_MODEL = "gemini-3.6-flash"
_ROLE_MAP = {"user": "user", "assistant": "model", "tool": "user", "system": "user"}


class GeminiClient:
    """LLMClient backed by the Gemini API. No google.genai type crosses this module's boundary."""

    def __init__(self, api_key: str | None = None, model: str = _MODEL) -> None:
        self._client = genai.Client(api_key=api_key or _load_api_key())
        self._model = model

    def complete(self, messages: list[Message], tools: list[dict[str, Any]]) -> dict[str, Any]:
        contents = [
            types.Content(role=_ROLE_MAP[message.role], parts=[types.Part.from_text(text=message.content)])
            for message in messages
        ]
        function_declarations = [
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"] or None,
            )
            for tool in tools
        ]
        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=function_declarations)] if function_declarations else None,
                temperature=0,
            ),
        )
        return _to_decision(response)


def _to_decision(response: types.GenerateContentResponse) -> dict[str, Any]:
    candidate = response.candidates[0]
    for part in candidate.content.parts or []:
        if part.function_call:
            return {"tool_name": part.function_call.name, "arguments": dict(part.function_call.args or {})}
    return {"final_message": response.text or ""}


def _load_api_key() -> str:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your environment or .env file.")
    return api_key
