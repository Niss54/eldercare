# On-Call Operations

## Shift Structure
- Weekday primary: Backend squad
- Weekday secondary: Platform squad
- Weekend primary: Rotating senior engineer

## Handover Checklist
- Review open incidents
- Review degraded service dashboards
- Confirm alert routes and paging targets
- Confirm rollback package availability

## Paging Targets
- API availability alerts: primary + secondary
- SOS unacknowledged alerts: primary + clinical escalation
- Queue lag alerts: primary + worker owner

## SLO Targets
- API availability: 99.9%
- SOS acknowledgement latency: p95 < 120 seconds
- Reminder dispatch latency: p95 < 60 seconds
