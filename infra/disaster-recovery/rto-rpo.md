# RTO and RPO Targets

- Recovery Time Objective (RTO): 60 minutes
- Recovery Point Objective (RPO): 15 minutes

## Validation
- Backup frequency: every 15 minutes for PostgreSQL WAL or equivalent
- Restore drill frequency: weekly in staging, monthly in production
- Failover simulation frequency: monthly
