from support_agent.tools.fixtures import CUSTOMERS


def account_lookup(customer_id: str) -> dict:
    """
    This is going to lookup the customer account information and return the recent orders, subscription details, and usage stats to the model for context.
    """
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        return {"error": f"unknown customer '{customer_id}'"}
    return {
        "customer_id": customer.customer_id,
        "plan": customer.plan,
        "subscription_status": customer.subscription_status,
        "renews_on": customer.renews_on,
        "usage": {
            "seats_used": customer.seats_used,
            "seats_limit": customer.seats_limit,
            "api_calls_this_month": customer.api_calls_this_month,
        },
        "order_ids": list(customer.order_ids),
    }
