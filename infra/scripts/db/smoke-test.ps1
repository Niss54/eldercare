$ErrorActionPreference = "Stop"

$compose = "infra/compose/docker-compose.dev.yml"
$envFile = ".env"

if (Test-Path $envFile) {
  foreach ($line in Get-Content $envFile) {
    if ($line -match "^\s*#" -or $line -notmatch "=") {
      continue
    }

    $parts = $line -split "=", 2
    $key = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"')

    if ($key -eq "POSTGRES_USER" -or $key -eq "POSTGRES_DB") {
      $existing = ""
      if (Test-Path "Env:$key") {
        $existing = (Get-Item "Env:$key").Value
      }

      if ([string]::IsNullOrWhiteSpace($existing)) {
        Set-Item -Path "Env:$key" -Value $value
      }
    }
  }
}

if (-not $env:POSTGRES_USER -or -not $env:POSTGRES_DB) {
  throw "POSTGRES_USER and POSTGRES_DB must be set (in environment or .env)."
}

./infra/scripts/db/migrate.ps1

$checks = @(
  "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('identity','consent','health','sos','marketplace','billing','analytics','audit') ORDER BY schema_name;",
  "SELECT COUNT(*) AS roles_count FROM identity.roles;",
  "SELECT COUNT(*) AS plans_count FROM billing.plans;",
  "SELECT COUNT(*) AS templates_count FROM notifications.templates;",
  "SELECT tablename FROM pg_tables WHERE schemaname = 'analytics' ORDER BY tablename;",
  "SELECT tablename FROM pg_tables WHERE schemaname = 'medication' AND tablename IN ('reminder_schedules','reminders_v2','adherence_records') ORDER BY tablename;",
  "SELECT tablename FROM pg_tables WHERE schemaname = 'notifications' AND tablename IN ('user_preferences','deliveries_v2','provider_callbacks_v2') ORDER BY tablename;",
  "SELECT tablename FROM pg_tables WHERE schemaname = 'sos' AND tablename IN ('incidents_v2','escalation_hops_v2','timeline_events_v2') ORDER BY tablename;",
  "SELECT tablename FROM pg_tables WHERE schemaname = 'marketplace' AND tablename IN ('caregivers_v2','credentials_v2','bookings_v2','ratings_v2','incident_reports_v2','extension_hooks') ORDER BY tablename;",
  "SELECT tablename FROM pg_tables WHERE schemaname = 'billing' AND tablename IN ('plan_catalog_v2','subscription_states_v2','invoices_v2','payment_events_v2','conversion_events_v2') ORDER BY tablename;",
  "SELECT indexname FROM pg_indexes WHERE schemaname = 'health' AND indexname IN ('idx_health_health_records_patient_type_created','idx_health_records_parent_type_created') ORDER BY indexname;",
  "SELECT indexname FROM pg_indexes WHERE schemaname = 'notifications' AND indexname = 'idx_notifications_deliveries_v2_recipient_status_created';",
  "SELECT indexname FROM pg_indexes WHERE schemaname = 'audit' AND indexname = 'idx_audit_audit_events_resource_time';"
)

foreach ($query in $checks) {
  Write-Host "Running check: $query" -ForegroundColor Cyan
  docker compose -f $compose --env-file $envFile exec -T postgres psql -v ON_ERROR_STOP=1 -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c $query
  if ($LASTEXITCODE -ne 0) {
    throw "Smoke check failed for query: $query"
  }
}

Write-Host "Database migration smoke tests passed." -ForegroundColor Green
