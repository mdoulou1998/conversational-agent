import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError

from support_agent.schemas.response import ResponseSchema
from support_agent.tools.actions import issue_refund, reset_password, create_support_ticket
from support_agent.tools.escalate import escalate_case
from support_agent.tools.account_lookup import account_lookup
from support_agent.tools.kb_search import kb_search

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

TOOLS = {
    "lookup_customer_order": account_lookup,
    "search_kb": kb_search,
    "escalate_case": escalate_case,
    "issue_refund": issue_refund,
    "reset_password": reset_password,
    "create_support_ticket": create_support_ticket,
}

def get_client() -> genai.Client:
    """
    Function to get a Gemini API client using the API key from environment variables.
    This ensures that the client is only created when app is running, and not at import time.
    """
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your environment or .env file.")
    return genai.Client(api_key=api_key)


def call_model(prompt: str, client: genai.Client | None = None) -> str:
    client = client or get_client()
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are a support agent for a SaaS product. "
                "Use tools when needed. "
                "Return ONLY valid JSON matching the required schema."
            ),
            temperature=0,
            response_mime_type="application/json",
        ),
    )
    return response.text


def support_agent(
    customer_id: str, query: str, client: genai.Client | None = None
) -> ResponseSchema:
    client = client or get_client()
    messages = [
        {
            "role": "user",
            "content": f"""
            Customer ID: {customer_id}
            Customer query: {query}
            """,
        }
    ]

    for _ in range(3):
        prompt = json.dumps(
            {
                "messages": messages,
                "available_tools": list(TOOLS.keys()),
                "output_schema": ResponseSchema.model_json_schema(),
            }
        )

        raw = call_model(prompt, client=client)
        try:
            payload = json.loads(raw)
            return ResponseSchema.model_validate(payload)
        except (json.JSONDecodeError, ValidationError):
            # In a real version, you could inspect the model output and decide
            # whether to retry or call a tool.
            # This is where the custom tool loop would live.
            pass

        # Example: if the model says it wants tool usage, execute a tool
        # and append the result back into the conversation.
        # This is the custom equivalent of a LangChain agent loop.
        tool_result = lookup_customer_order(customer_id)
        messages.append({"role": "tool", "content": json.dumps(tool_result)})

    raise RuntimeError("Agent failed to return valid structured output.")


if __name__ == "__main__":
    result = support_agent("12345", "My order is late and I need help.")
    print(result.model_dump())
