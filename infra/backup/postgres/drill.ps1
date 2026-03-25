$ErrorActionPreference = "Stop"

./infra/backup/postgres/backup.ps1
$latest = Get-ChildItem backups/postgres_*.sql | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $latest) {
  throw "No backup found for drill"
}

./infra/backup/postgres/restore.ps1 -BackupFile $latest.FullName
./infra/scripts/db/smoke-test.ps1
Write-Host "Backup/restore drill completed successfully." -ForegroundColor Green
