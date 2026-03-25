# Staging Dry-Run and Failover Drill Evidence

- Generated at: 2026-03-25 20:16:08 +05:30
- Workspace: C:\Users\nisha\OneDrive\Documents\eldercare
- Passed checks: 5
- Failed checks: 

## Results

| Area | Check | Status | Evidence | Details |
|---|---|---|---|---|
| Staging Dry-Run | Staging checklist exists | PASS | docs/runbooks/staging-signoff-checklist.md | Checklist present |
| Staging Dry-Run | Staging compose model resolves | PASS | docker-compose.staging.yml | docker compose config succeeded |
| Data Volume | Production-like load profile report exists | PASS | tools/performance/reports | Found report: C:\Users\nisha\OneDrive\Documents\eldercare\tools\performance\reports\20260325-113124\ramp-summary.json |
| Failover Drill | Failover playbook exists | PASS | infra/disaster-recovery/failover-playbooks/api-failover.md | Failover playbook present |
| Failover Drill | Compose failover rehearsal command path validated | FAIL | infra/compose/docker-compose.dev.yml | ExitCode=1 / Output=docker.exe : failed to connect to the docker API at  npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if  the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system  cannot find the file specified. At C:\Users\nisha\OneDrive\Documents\eldercare\infra\scripts\release\staging-dr y-run-failover.ps1:57 char:13 +   $output = & $Command @CommandArgs 2>&1 +             ~~~~~~~~~~~~~~~~~~~~~~~~~~~~     + CategoryInfo          : NotSpecified: (failed to conne...file specified.     :String) [], RemoteException     + FullyQualifiedErrorId : NativeCommandError |
| Failover Drill | Rollback checklist exists | PASS | docs/runbooks/production-deployment-checklist.md | Rollback checklist present |

## Completion Guidance

- All checks must pass before marking staging dry-run and failover drill as complete.
- If Docker checks fail, start Docker daemon and rerun this script.
