from datetime import UTC, datetime

from src.workers.task_dispatcher import dispatch_task


def queue_and_dispatch_due() -> dict:
    batch_id = f"api-medication-{int(datetime.now(UTC).timestamp())}"
    return dispatch_task(
        "medication.dispatch_due",
        args=[batch_id],
        kwargs={"idempotency_key": batch_id},
    )
