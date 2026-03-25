# Scheduler Replay and Compensation Runbook

## Trigger Conditions
- queue.scheduler.dlq receives failed critical tasks.
- Alerts fire for high queue lag, retry surge, or dead-letter growth.

## Immediate Stabilization
1. Pause non-critical beat entries (notification heartbeat and analytics jobs).
2. Keep SOS and medication windows active.
3. Verify Redis health and worker availability.

## Replay Procedure
1. Inspect failed envelopes from scheduler.dead_letter output.
2. Group failures by task name and root cause.
3. Re-dispatch in safe order:
   - medication.dispatch_due
   - sos.process_escalation
   - notifications.dispatch
4. Preserve original idempotency keys when replaying to avoid duplicate side effects.

## Manual Compensation
- Medication miss: create corrective reminder dispatch and log incident note.
- SOS delay: trigger immediate escalation level and notify on-call clinician.
- Notification failure: fallback to alternate channel and record provider failure.

## Post-Recovery Verification
- queue lag below threshold for 15 minutes.
- dead_letter_events_total stable.
- No unacknowledged critical SOS incidents.
- Run full scheduler smoke checks in staging.

## Launch Validation Evidence
Before signoff, run:

```powershell
./infra/scripts/scheduler/validate-backpressure.ps1
```

Record output JSON and ensure `VALIDATION_PASS` is present.
