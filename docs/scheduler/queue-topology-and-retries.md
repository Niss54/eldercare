# Scheduler Queue Topology and Retry Policies

## Queue Topology
Exchange: eldercare (topic)

Queues and routing keys:
- queue.medication: medication.#
- queue.notifications: notifications.#
- queue.sos: sos.#
- queue.scheduler: scheduler.#
- queue.scheduler.dlq: scheduler.dlq

Task routes:
- medication.dispatch_due -> queue.medication (medication.dispatch)
- notifications.dispatch -> queue.notifications (notifications.dispatch)
- sos.process_escalation -> queue.sos (sos.escalation)
- scheduler.dispatch_medication_window -> queue.scheduler (scheduler.medication.window)
- scheduler.dispatch_sos_escalation_sweep -> queue.scheduler (scheduler.sos.escalation)
- scheduler.dispatch_notification_heartbeat -> queue.scheduler (scheduler.notifications.heartbeat)
- scheduler.dead_letter -> queue.scheduler.dlq (scheduler.dlq)

## Beat Schedule Coverage
- Medication windows: every minute.
- Medication escalation sweep: every 2 minutes.
- SOS escalation sweep level 1: every minute.
- SOS escalation sweep level 2: every 3 minutes.
- Notification heartbeat: every 5 minutes.
- Scheduler metrics heartbeat: every minute.

## Retry Policy Template
All critical worker tasks use:
- autoretry_for: Exception
- retry_backoff: true
- retry_backoff_max: 300 seconds
- retry_jitter: true
- max_retries: 5

## Dead-Letter Strategy
On task failure, task_failure signal forwards failure envelope to scheduler.dead_letter on queue.scheduler.dlq.

## Lock and Dedup Strategy
- Scheduler lock: Redis SET NX with TTL to prevent duplicate dispatches across beat instances.
- Task dedup: Redis SET NX with TTL on idempotency key per task type.
- Duplicate dispatches are skipped and tracked in metrics counters.

## Metrics Exposed
- scheduler_dispatches_total
- scheduler_lock_skips_total
- dedup_skips_total
- task_retries_total
- task_failures_total
- dead_letter_events_total
- queue_lag_seconds

## Backpressure and Dead-Letter Validation
Run the launch validation script to verify backpressure signals and retry/dead-letter flow:

```powershell
./infra/scripts/scheduler/validate-backpressure.ps1
```

Validation checks:
- `task_retries_total` increments.
- `task_failures_total` increments.
- `dead_letter_events_total` increments.
- Queue lag heartbeat reports `queue_lag_seconds` at expected value.
