from src.workers.task_dispatcher import dispatch_task


def send_email(recipient_id: str, type: str, data: dict) -> dict:
    message = str(data.get("message") or type)
    priority = str(data.get("priority") or "routine")
    return dispatch_task(
        "notifications.dispatch",
        args=[recipient_id, "email", message, priority],
        kwargs={"idempotency_key": str(data.get("idempotency_key") or f"email:{recipient_id}:{type}")},
    )


def send_sms(recipient_id: str, type: str, data: dict) -> dict:
    message = str(data.get("message") or type)
    priority = str(data.get("priority") or "routine")
    return dispatch_task(
        "notifications.dispatch",
        args=[recipient_id, "sms", message, priority],
        kwargs={"idempotency_key": str(data.get("idempotency_key") or f"sms:{recipient_id}:{type}")},
    )
