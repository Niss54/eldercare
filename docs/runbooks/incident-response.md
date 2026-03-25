# Incident Response Runbook

## Severity Levels
- SEV-1: Patient safety risk, data breach, or complete outage
- SEV-2: Core workflow degraded, no immediate patient-safety impact
- SEV-3: Minor degradation, workaround available

## Immediate Actions
1. Acknowledge alert in on-call system within 5 minutes.
2. Open incident channel and assign incident commander.
3. Capture current blast radius and impacted roles.
4. Stabilize service using rollback, traffic shift, or feature flag.

## Escalation Matrix
- Primary on-call: Platform engineer
- Secondary on-call: Backend engineer
- Clinical escalation contact: Care operations lead
- Executive escalation: CTO for SEV-1

## Communication Cadence
- SEV-1: every 15 minutes
- SEV-2: every 30 minutes
- SEV-3: hourly

## Resolution Checklist
- Incident mitigated and monitored for 30 minutes
- Root cause identified
- Corrective tasks logged with owners and due dates
- Postmortem completed within 48 hours
