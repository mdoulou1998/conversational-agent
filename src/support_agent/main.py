from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from support_agent.schemas.response import ResponseSchema

load_dotenv(dotenv_path=ROOT / ".env")

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash")

agent = create_agent(
    model=llm,
    tools=[],
    system_prompt=(
        "You are a support agent. Respond to the customer query in a helpful and concise manner. "
        "Return a structured response that matches the provided schema."
    ),
    response_format=ResponseSchema,
)

customer_id = "12345"
query = "My order is late and I need help."

result = agent.invoke(
    {
        "messages": [
            HumanMessage(
                content=f"Customer ID: {customer_id}\nCustomer Query: {query}"
            )
        ]
    }
)

final_message = result["messages"][-1]
content = final_message.content
if isinstance(content, list):
    content = "".join(
        part.get("text", "") if isinstance(part, dict) else str(part)
        for part in content
    )

parsed = ResponseSchema.model_validate_json(content)
print(parsed.model_dump())