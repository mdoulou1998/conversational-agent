"""Deterministic, realistic fixture data standing in for the account, order,
and knowledge-base systems the brief says can be stubbed.

Two customers, three orders, four KB chunks. order-1 and order-2 belong to
cust-1; order-3 belongs to cust-2. That uneven split is deliberate: if a
script has cust-2 try to refund order-1, that's the adversarial cross-customer
refund case - an order that exists, just not for the customer asking.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    email: str
    plan: str
    subscription_status: str
    renews_on: str
    seats_used: int
    seats_limit: int
    api_calls_this_month: int
    order_ids: tuple[str, ...]


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    item: str
    total: float


@dataclass(frozen=True)
class KBChunk:
    topic: str
    text: str


CUSTOMERS: dict[str, Customer] = {
    "cust-1": Customer(
        customer_id="cust-1",
        name="Amelia Chen",
        email="amelia.chen@example.com",
        plan="pro",
        subscription_status="active",
        renews_on="2026-04-01",
        seats_used=4,
        seats_limit=5,
        api_calls_this_month=128_400,
        order_ids=("order-1", "order-2"),
    ),
    "cust-2": Customer(
        customer_id="cust-2",
        name="Ben Osei",
        email="ben.osei@example.com",
        plan="starter",
        subscription_status="active",
        renews_on="2026-04-05",
        seats_used=1,
        seats_limit=1,
        api_calls_this_month=2_150,
        order_ids=("order-3",),
    ),
}  # frozen

ORDERS: dict[str, Order] = {
    "order-1": Order(
        order_id="order-1", customer_id="cust-1", item="Pro plan subscription - March", total=49.99
    ),
    "order-2": Order(order_id="order-2", customer_id="cust-1", item="Additional seat", total=19.99),
    "order-3": Order(
        order_id="order-3",
        customer_id="cust-2",
        item="Starter plan subscription - March",
        total=15.00,
    ),
}  # frozen

KB_CHUNKS: list[KBChunk] = [
    KBChunk(
        topic="password reset",
        text="To reset your password, go to Settings > Security and click 'Reset Password'.",
    ),
    KBChunk(
        topic="refund policy",
        text="Refunds are available within 30 days of purchase, up to $50 per request.",
    ),
    KBChunk(
        topic="billing cycle",
        text="Your plan renews monthly on the day you first subscribed.",
    ),
    KBChunk(
        topic="cancel subscription",
        text="You can cancel your subscription anytime from Settings > Billing > Cancel Plan.",
    ),
]  # frozen
