$ErrorActionPreference = "Stop"

if (-not (Test-Path "backups")) {
  New-Item -ItemType Directory -Path "backups" | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile = "backups/postgres_$timestamp.sql"

docker compose -f infra/compose/docker-compose.dev.yml --env-file .env exec -T postgres pg_dump -U $env:POSTGRES_USER -d $env:POSTGRES_DB > $outputFile

if (-not (Test-Path $outputFile)) {
  throw "Backup file was not created"
}

Write-Host "Postgres backup created at $outputFile" -ForegroundColor Green
