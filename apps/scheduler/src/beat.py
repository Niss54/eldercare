import os

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

beat = Celery("eldercare_scheduler", broker=broker_url, backend=result_backend)
beat.conf.timezone = "UTC"
module_exchange = Exchange("eldercare", type="topic")

beat.conf.update(
    task_default_exchange="eldercare",
    task_default_exchange_type="topic",
    task_default_routing_key="scheduler.default",
    task_queues=(
        Queue("queue.medication", module_exchange, routing_key="medication.#"),
        Queue("queue.notifications", module_exchange, routing_key="notifications.#"),
        Queue("queue.sos", module_exchange, routing_key="sos.#"),
        Queue("queue.scheduler", module_exchange, routing_key="scheduler.#"),
        Queue("queue.scheduler.dlq", module_exchange, routing_key="scheduler.dlq"),
    ),
    task_routes={
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
        "scheduler.metrics": {"queue": "queue.scheduler", "routing_key": "scheduler.metrics"},
    },
)

beat.conf.beat_schedule = {
    "medication-window-dispatch-every-minute": {
        "task": "scheduler.dispatch_medication_window",
        "schedule": crontab(minute="*"),
        "args": ("scheduled-medication-batch",),
    },
    "medication-escalation-sweep-every-2-min": {
        "task": "scheduler.dispatch_medication_window",
        "schedule": crontab(minute="*/2"),
        "args": ("medication-escalation-sweep",),
    },
    "sos-escalation-sweep-every-minute": {
        "task": "scheduler.dispatch_sos_escalation_sweep",
        "schedule": crontab(minute="*"),
        "args": ("scheduled-incident", 1),
    },
    "sos-escalation-level-2-every-3-min": {
        "task": "scheduler.dispatch_sos_escalation_sweep",
        "schedule": crontab(minute="*/3"),
        "args": ("scheduled-incident", 2),
    },
    "notification-heartbeat-every-5-min": {
        "task": "scheduler.dispatch_notification_heartbeat",
        "schedule": crontab(minute="*/5"),
        "args": ("u_family", "in_app", "scheduled-check-in", "routine"),
    },
    "consent-expiry-sweep-every-6-hours": {
        "task": "scheduler.dispatch_consent_expiry_sweep",
        "schedule": crontab(minute="0", hour="*/6"),
        "args": (3,),
    },
    "scheduler-metrics-heartbeat-every-minute": {
        "task": "scheduler.metrics",
        "schedule": crontab(minute="*"),
        "args": (0.0,),
    },
}
