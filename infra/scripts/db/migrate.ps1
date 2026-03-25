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

$migrationFiles = @(
  "apps/api/src/integrations/db/migrations/versions/001_initial_schema.sql",
  "apps/api/src/integrations/db/migrations/versions/002_family_invitations.sql",
  "apps/api/src/integrations/db/migrations/versions/003_audit_events_append_only.sql",
  "apps/api/src/integrations/db/policies/consent_filters.sql",
  "apps/api/src/integrations/db/migrations/versions/004_health_records.sql",
  "apps/api/src/integrations/db/migrations/versions/005_care_ops_growth_persistence_alignment.sql",
  "apps/api/src/integrations/db/migrations/versions/006_db_performance_tuning.sql",
  "apps/api/src/integrations/db/policies/row_level_security.sql",
  "apps/api/src/integrations/db/migrations/seeds/001_non_phi_seed.sql"
)

foreach ($file in $migrationFiles) {
  if (-not (Test-Path $file)) {
    throw "Missing migration asset: $file"
  }

  Write-Host "Applying $file" -ForegroundColor Cyan
  Get-Content $file | docker compose -f $compose --env-file $envFile exec -T postgres psql -v ON_ERROR_STOP=1 -U $env:POSTGRES_USER -d $env:POSTGRES_DB
  if ($LASTEXITCODE -ne 0) {
    throw "Migration step failed for $file"
  }
}

Write-Host "Database migration and seed sequence completed." -ForegroundColor Green
