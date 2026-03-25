import os
from datetime import UTC, datetime
from typing import Any

from celery import Celery


_broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
_backend_url = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
_dispatch_client = Celery("eldercare_api_dispatcher", broker=_broker_url, backend=_backend_url)


def dispatch_task(task_name: str, args: list[Any] | None = None, kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or []
    kwargs = kwargs or {}
    result = _dispatch_client.send_task(task_name, args=args, kwargs=kwargs)
    return {
        "status": "queued",
        "task_name": task_name,
        "task_id": result.id,
        "queued_at": datetime.now(UTC).isoformat(),
    }
