apps/worker/
├─ pyproject.toml
├─ src/
│  ├─ celery_app.py
│  ├─ queues.py
│  ├─ tasks/
│  │  ├─ notifications/
│  │  ├─ medication_reminders/
│  │  ├─ sos_cascade/
│  │  ├─ audit_export/
│  │  ├─ analytics_rollups/
│  │  ├─ subscriptions_billing/
│  │  ├─ ai_jobs/
│  │  └─ iot_ingestion/
│  ├─ consumers/
│  └─ retries/
└─ tests/

apps/scheduler/
├─ pyproject.toml
├─ src/
│  ├─ beat.py
│  ├─ schedules/
│  │  ├─ medication_windows.py
│  │  ├─ reminder_escalation.py
│  │  ├─ stale_sos_watchdog.py
│  │  ├─ consent_expiry_checks.py
│  │  ├─ subscription_renewals.py
│  │  └─ analytics_snapshots.py
│  └─ clocks/
└─ tests/