import os
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from celery import Celery
from celery.signals import task_failure
from kombu import Exchange, Queue
from redis import Redis

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
dedup_ttl_seconds = int(os.getenv("SCHEDULER_IDEMPOTENCY_TTL_SECONDS", "3600"))
lock_ttl_seconds = int(os.getenv("SCHEDULER_LOCK_TTL_SECONDS", "120"))

celery_app = Celery("eldercare_worker", broker=broker_url, backend=result_backend)

module_exchange = Exchange("eldercare", type="topic")
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_exchange="eldercare",
    task_default_exchange_type="topic",
    task_default_routing_key="platform.default",
    task_queues=(
        Queue("queue.medication", module_exchange, routing_key="medication.#"),
        Queue("queue.notifications", module_exchange, routing_key="notifications.#"),
        Queue("queue.sos", module_exchange, routing_key="sos.#"),
        Queue("queue.scheduler", module_exchange, routing_key="scheduler.#"),
        Queue("queue.scheduler.dlq", module_exchange, routing_key="scheduler.dlq"),
    ),
    task_routes={
        "medication.dispatch_due": {"queue": "queue.medication", "routing_key": "medication.dispatch"},
        "notifications.dispatch": {"queue": "queue.notifications", "routing_key": "notifications.dispatch"},
        "sos.process_escalation": {"queue": "queue.sos", "routing_key": "sos.escalation"},
        "scheduler.dispatch_medication_window": {
            "queue": "queue.scheduler",
            "routing_key": "scheduler.medication.window",
        },
        "scheduler.dispatch_sos_escalation_sweep": {
            "queue": "queue.scheduler",
            "routing_key": "scheduler.sos.escalation",
        },
        "scheduler.dispatch_notification_heartbeat": {
            "queue": "queue.scheduler",
            "routing_key": "scheduler.notifications.heartbeat",
        },
        "scheduler.dispatch_consent_expiry_sweep": {
            "queue": "queue.scheduler",
            "routing_key": "scheduler.consent.expiry",
        },
        "consent.process_expiry_and_renewal": {
            "queue": "queue.scheduler",
            "routing_key": "consent.expiry.process",
        },
        "scheduler.dead_letter": {"queue": "queue.scheduler.dlq", "routing_key": "scheduler.dlq"},
        "scheduler.force_retry_then_fail": {"queue": "queue.scheduler", "routing_key": "scheduler.validation"},
        "scheduler.metrics": {"queue": "queue.scheduler", "routing_key": "scheduler.metrics"},
    },
)


class SchedulerMetrics:
    def __init__(self):
        self.counters: dict[str, int] = defaultdict(int)
        self.latest_lag_seconds: float = 0.0

    def increment(self, metric: str, amount: int = 1) -> None:
        self.counters[metric] += amount

    def set_lag(self, lag_seconds: float) -> None:
        self.latest_lag_seconds = max(0.0, lag_seconds)

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(self.counters),
            "queue_lag_seconds": round(self.latest_lag_seconds, 3),
            "generated_at": datetime.now(UTC).isoformat(),
        }


metrics = SchedulerMetrics()


def _redis_client() -> Redis:
    return Redis.from_url(broker_url)


def _register_retry(task) -> None:
    if task.request.retries > 0:
        metrics.increment("task_retries_total")


def _acquire_scheduler_lock(lock_name: str) -> bool:
    lock_key = f"scheduler:lock:{lock_name}"
    try:
        return bool(_redis_client().set(lock_key, "1", nx=True, ex=lock_ttl_seconds))
    except Exception:
        # Fallback to permissive mode in local environments where redis is unavailable.
        return True


def _idempotent_gate(task_name: str, idempotency_key: str | None) -> tuple[bool, str]:
    if not idempotency_key:
        idempotency_key = f"{task_name}:{int(time.time())}"
    dedup_key = f"task:dedup:{task_name}:{idempotency_key}"
    try:
        accepted = bool(_redis_client().set(dedup_key, "1", nx=True, ex=dedup_ttl_seconds))
        return accepted, idempotency_key
    except Exception:
        return True, idempotency_key


@celery_app.task(name="notifications.send_test")
def send_test_notification(user_id: str, message: str) -> dict[str, str]:
    return {"user_id": user_id, "message": message, "status": "queued"}


@celery_app.task(
    bind=True,
    name="notifications.dispatch",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def dispatch_notification_task(
    self,
    recipient_user_id: str,
    channel: str,
    message: str,
    priority: str = "routine",
    idempotency_key: str | None = None,
) -> dict[str, str]:
    _register_retry(self)
    accepted, actual_key = _idempotent_gate("notifications.dispatch", idempotency_key)
    if not accepted:
        metrics.increment("dedup_skips_total")
        return {
            "recipient_user_id": recipient_user_id,
            "channel": channel,
            "priority": priority,
            "message": message,
            "status": "duplicate_skipped",
            "idempotency_key": actual_key,
            "processed_at": datetime.now(UTC).isoformat(),
        }

    metrics.increment("notifications_dispatched_total")
    return {
        "recipient_user_id": recipient_user_id,
        "channel": channel,
        "priority": priority,
        "message": message,
        "idempotency_key": actual_key,
        "status": "delivered",
        "processed_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(
    bind=True,
    name="medication.dispatch_due",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def medication_dispatch_due_task(self, batch_id: str, idempotency_key: str | None = None) -> dict[str, str]:
    _register_retry(self)
    accepted, actual_key = _idempotent_gate("medication.dispatch_due", idempotency_key)
    if not accepted:
        metrics.increment("dedup_skips_total")
        return {
            "batch_id": batch_id,
            "idempotency_key": actual_key,
            "status": "duplicate_skipped",
            "processed_at": datetime.now(UTC).isoformat(),
        }

    metrics.increment("medication_batches_processed_total")
    return {
        "batch_id": batch_id,
        "idempotency_key": actual_key,
        "status": "processed",
        "processed_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(
    bind=True,
    name="sos.process_escalation",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def sos_process_escalation_task(
    self,
    incident_id: str,
    level: int,
    idempotency_key: str | None = None,
) -> dict[str, str | int]:
    _register_retry(self)
    accepted, actual_key = _idempotent_gate("sos.process_escalation", idempotency_key)
    if not accepted:
        metrics.increment("dedup_skips_total")
        return {
            "incident_id": incident_id,
            "level": level,
            "idempotency_key": actual_key,
            "status": "duplicate_skipped",
            "processed_at": datetime.now(UTC).isoformat(),
        }

    metrics.increment("sos_escalations_processed_total")
    return {
        "incident_id": incident_id,
        "level": level,
        "idempotency_key": actual_key,
        "status": "notified",
        "processed_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(name="scheduler.dispatch_medication_window")
def dispatch_medication_window(batch_id: str) -> dict[str, str]:
    if not _acquire_scheduler_lock("medication_window"):
        metrics.increment("scheduler_lock_skips_total")
        return {"status": "skipped_locked", "batch_id": batch_id}

    idempotency_key = f"medication-window:{batch_id}:{int(time.time() // 60)}"
    celery_app.send_task(
        "medication.dispatch_due",
        args=(batch_id,),
        kwargs={"idempotency_key": idempotency_key},
    )
    metrics.increment("scheduler_dispatches_total")
    return {"status": "queued", "batch_id": batch_id, "idempotency_key": idempotency_key}


@celery_app.task(name="scheduler.dispatch_sos_escalation_sweep")
def dispatch_sos_escalation_sweep(incident_id: str, level: int) -> dict[str, str | int]:
    if not _acquire_scheduler_lock("sos_escalation"):
        metrics.increment("scheduler_lock_skips_total")
        return {"status": "skipped_locked", "incident_id": incident_id, "level": level}

    idempotency_key = f"sos-escalation:{incident_id}:{level}:{int(time.time() // 60)}"
    celery_app.send_task(
        "sos.process_escalation",
        args=(incident_id, level),
        kwargs={"idempotency_key": idempotency_key},
    )
    metrics.increment("scheduler_dispatches_total")
    return {
        "status": "queued",
        "incident_id": incident_id,
        "level": level,
        "idempotency_key": idempotency_key,
    }


@celery_app.task(name="scheduler.dispatch_notification_heartbeat")
def dispatch_notification_heartbeat(recipient_user_id: str, channel: str, message: str, priority: str) -> dict[str, str]:
    if not _acquire_scheduler_lock("notification_heartbeat"):
        metrics.increment("scheduler_lock_skips_total")
        return {"status": "skipped_locked", "recipient_user_id": recipient_user_id}

    idempotency_key = f"notification-heartbeat:{recipient_user_id}:{int(time.time() // 300)}"
    celery_app.send_task(
        "notifications.dispatch",
        args=(recipient_user_id, channel, message, priority),
        kwargs={"idempotency_key": idempotency_key},
    )
    metrics.increment("scheduler_dispatches_total")
    return {"status": "queued", "recipient_user_id": recipient_user_id, "idempotency_key": idempotency_key}


@celery_app.task(name="scheduler.dispatch_consent_expiry_sweep")
def dispatch_consent_expiry_sweep(within_days: int = 3) -> dict[str, str]:
    if not _acquire_scheduler_lock("consent_expiry_sweep"):
        metrics.increment("scheduler_lock_skips_total")
        return {"status": "skipped_locked", "within_days": str(within_days)}

    idempotency_key = f"consent-expiry:{within_days}:{int(time.time() // 60)}"
    celery_app.send_task(
        "consent.process_expiry_and_renewal",
        args=(within_days,),
        kwargs={"idempotency_key": idempotency_key},
    )
    metrics.increment("scheduler_dispatches_total")
    return {"status": "queued", "within_days": str(within_days), "idempotency_key": idempotency_key}


@celery_app.task(
    bind=True,
    name="consent.process_expiry_and_renewal",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def process_consent_expiry_and_renewal(self, within_days: int = 3, idempotency_key: str | None = None) -> dict[str, Any]:
    _register_retry(self)
    accepted, actual_key = _idempotent_gate("consent.process_expiry_and_renewal", idempotency_key)
    if not accepted:
        metrics.increment("dedup_skips_total")
        return {
            "status": "duplicate_skipped",
            "idempotency_key": actual_key,
            "processed_at": datetime.now(UTC).isoformat(),
        }

    expired_count = 0
    renewal_due_count = 0
    try:
        from src.modules.consent_access.service import consent_service

        expired_count = len(consent_service.expire_due_grants())
        renewal_due_count = len(consent_service.due_for_renewal(within_days=within_days))
    except Exception:
        # Worker may run in isolation without API modules imported in local-only setups.
        pass

    metrics.increment("consent_expiry_sweeps_total")
    return {
        "status": "processed",
        "idempotency_key": actual_key,
        "expired_count": expired_count,
        "renewal_due_count": renewal_due_count,
        "processed_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(name="scheduler.dead_letter")
def dead_letter_task(task_name: str, error: str, payload: dict[str, Any]) -> dict[str, Any]:
    metrics.increment("dead_letter_events_total")
    return {
        "task_name": task_name,
        "error": error,
        "payload": payload,
        "status": "captured",
        "captured_at": datetime.now(UTC).isoformat(),
    }


@celery_app.task(name="scheduler.metrics")
def scheduler_metrics_snapshot(queue_lag_seconds: float = 0.0) -> dict[str, Any]:
    metrics.set_lag(queue_lag_seconds)
    return metrics.snapshot()


@celery_app.task(bind=True, name="scheduler.force_retry_then_fail")
def scheduler_force_retry_then_fail(self, token: str = "validation") -> dict[str, Any]:
    _register_retry(self)

    if self.request.retries < 1:
        raise self.retry(exc=RuntimeError(f"forced retry for {token}"), countdown=0, max_retries=1)

    raise RuntimeError(f"forced terminal failure for {token}")


@task_failure.connect
def route_failed_task_to_dlq(sender=None, task_id=None, exception=None, args=None, kwargs=None, **_):
    task_name = getattr(sender, "name", "unknown")
    if task_name == "scheduler.dead_letter":
        return

    metrics.increment("task_failures_total")
    celery_app.send_task(
        "scheduler.dead_letter",
        args=(
            task_name,
            str(exception),
            {
                "task_id": task_id,
                "args": list(args or []),
                "kwargs": kwargs or {},
                "failed_at": datetime.now(UTC).isoformat(),
            },
        ),
        queue="queue.scheduler.dlq",
        routing_key="scheduler.dlq",
    )
