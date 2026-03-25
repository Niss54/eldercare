# Staging Signoff Checklist

- [ ] CI pipeline green for api/web/compose/security scans
- [ ] API regression tests pass
- [ ] Web lint and production build pass
- [ ] Security middleware and rate-limit checks validated
- [ ] Load test thresholds pass (tools/performance/k6_smoke.js)
- [ ] Failure-mode checks pass (tools/performance/failure_mode_checks.ps1)
- [ ] Backup/restore drill executed successfully
- [ ] Alert rules loaded and test alert fired
- [ ] Incident runbook dry run performed
- [ ] Release candidate approved by engineering lead
