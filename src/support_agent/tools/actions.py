import hashlib

from support_agent.tools.fixtures import CUSTOMERS, ORDERS


def issue_refund(order_id: str, amount: float) -> dict:
    """
    Issues a refund for a given order ID and amount. This will initiate the refund process and
    return the status of the refund.
    """
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": f"order '{order_id}' does not exist"}
    return {"status": "refunded", "order_id": order_id, "amount": amount}


def reset_password(customer_id: str) -> dict:
    """
    Initiates a password reset for the given customer ID. This will send a password reset email to the
    customer's registered email address.
    """
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        return {"error": f"unknown customer '{customer_id}'"}
    return {"status": "reset_email_sent", "sent_to": customer.email}


def create_support_ticket(customer_id: str, summary: str, priority: str) -> dict:
    """
    Creates a support ticket for the given customer ID with the specified summary and priority.
    """
    digest = hashlib.sha256(f"{customer_id}:{summary}".encode()).hexdigest()[:8]
    return {"status": "created", "ticket_id": f"TCK-{digest}", "priority": priority}
