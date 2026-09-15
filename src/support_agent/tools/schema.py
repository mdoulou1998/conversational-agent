"""Tool schemas in the shape ToolRegistry.schema() hands to the LLM:
{"name", "description", "parameters"} per tool, no provider-specific wrapper.

Names and descriptions mirror the TOOLS registry in agent_main.py so there is
one description of what the model sees, not two that can drift apart.
"""

tools = [
    {
        "name": "lookup_customer_order",
        "description": "Looks up a customer's recent orders, subscription, and usage details.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's unique identifier",
                }
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_kb",
        "description": "Searches the product knowledge base and returns the top matching chunks.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "top_k": {
                    "type": "integer",
                    "description": "The number of top results to return",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "escalate_case",
        "description": "Escalates a support case to a human with a reason.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's unique identifier",
                },
                "reason": {
                    "type": "string",
                    "description": "Why this case needs a human",
                },
            },
            "required": ["customer_id", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "issue_refund",
        "description": "Issues a refund for a given order ID and amount.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order to refund",
                },
                "amount": {
                    "type": "number",
                    "description": "The refund amount",
                },
            },
            "required": ["order_id", "amount"],
            "additionalProperties": False,
        },
    },
    {
        "name": "reset_password",
        "description": "Initiates a password reset for a customer.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's unique identifier",
                }
            },
            "required": ["customer_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_support_ticket",
        "description": "Creates a support ticket for a customer with a summary and priority.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer's unique identifier",
                },
                "summary": {
                    "type": "string",
                    "description": "A short summary of the issue",
                },
                "priority": {
                    "type": "string",
                    "description": "Ticket priority",
                    "enum": ["low", "medium", "high"],
                },
            },
            "required": ["customer_id", "summary", "priority"],
            "additionalProperties": False,
        },
    },
]
