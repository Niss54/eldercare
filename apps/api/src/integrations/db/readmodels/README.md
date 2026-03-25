# Analytics Read Models

The analytics schema stores pre-aggregated rollups used by admin dashboards and operational reports.

Current read models:
- analytics.user_activity_daily
- analytics.incident_rollups_hourly
- analytics.notification_rollups_hourly
- analytics.revenue_rollups_monthly

These tables are intentionally write-optimized for batch jobs and materialization workers.
