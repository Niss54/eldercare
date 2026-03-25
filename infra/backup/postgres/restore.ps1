param(
  [Parameter(Mandatory = $true)]
  [string]$BackupFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
  throw "Backup file not found: $BackupFile"
}

Get-Content $BackupFile | docker compose -f infra/compose/docker-compose.dev.yml --env-file .env exec -T postgres psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB

Write-Host "Postgres restore completed from $BackupFile" -ForegroundColor Green
