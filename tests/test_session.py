import pytest

from support_agent.schemas.domain import Message
from support_agent.session import Session


def test_user_message_can_enter() -> None:
    session = Session(customer_id="cust-123")
    session.add_user_message("My order is late")

    assert len(session.messages) == 1
    assert session.messages[0].role == "user"
    assert session.messages[0].content == "My order is late"


def test_blank_message_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        Message(role="user", content="   ")


def test_customer_id_is_validated() -> None:
    session = Session()
    session.set_customer_id("cust-456")

    assert session.customer_id == "cust-456"

    with pytest.raises(ValueError, match="customer_id cannot be empty"):
        session.set_customer_id("   ")
