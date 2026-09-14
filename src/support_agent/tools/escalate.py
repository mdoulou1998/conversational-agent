def escalate_case(customer_id: str, reason: str):
    """
    Escalates a support case for a given customer ID with a specified reason.
    """
    return {"case_id": f"ESC-{customer_id}", "status": "opened", "reason": reason}
