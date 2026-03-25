# Staging Failover Dry-Run

## Objective
- Rehearse staging launch with production-like data volume checks.
- Rehearse API failover/rollback workflow end-to-end.

## Prerequisites
- Docker daemon running.
- `.env` present at repository root.
- Latest load report available under `tools/performance/reports/*/ramp-summary.json`.

## Execution
1. Generate evidence report:

```powershell
./infra/scripts/release/staging-dry-run-failover.ps1
```

2. If Docker is available, execute operational failover rehearsal:

```powershell
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env up -d
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env stop api
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env up -d api
./infra/scripts/dev-health.ps1
```

3. Confirm failover playbook aligns with rehearsal outcomes:
- `infra/disaster-recovery/failover-playbooks/api-failover.md`

## Pass Criteria
- Dry-run report contains zero failed checks.
- API service health returns to green after failover/restore simulation.
- No unresolved critical alerts during the drill window.