$ErrorActionPreference = "Stop"

$compose = "infra/compose/docker-compose.dev.yml"
$envFile = ".env"
$slowBudgetFromEnvFile = $null

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

    if ($key -eq "SLOW_QUERY_BUDGET_MS") {
      $slowBudgetFromEnvFile = $value
    }
  }
}

if (-not $env:POSTGRES_USER -or -not $env:POSTGRES_DB) {
  throw "POSTGRES_USER and POSTGRES_DB must be set (in environment or .env)."
}

$slowMs = 200
if ($env:SLOW_QUERY_BUDGET_MS) {
  $slowMs = [int]$env:SLOW_QUERY_BUDGET_MS
} elseif ($slowBudgetFromEnvFile) {
  $slowMs = [int]$slowBudgetFromEnvFile
}

Write-Host "Checking DB performance budget (slow query threshold: ${slowMs}ms)..." -ForegroundColor Cyan

$queries = @(
  "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;",
  "SELECT count(*) AS missing_indexes FROM pg_indexes WHERE schemaname IN ('health','sos','notifications','marketplace','billing','consent','family','audit') AND indexname LIKE 'idx_%';",
  "SELECT queryid, round(mean_exec_time::numeric,2) AS mean_ms, calls, rows FROM pg_stat_statements WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database()) ORDER BY mean_exec_time DESC LIMIT 20;",
  "SELECT count(*) AS over_budget FROM pg_stat_statements WHERE mean_exec_time > ${slowMs};"
)

foreach ($query in $queries) {
  docker compose -f $compose --env-file $envFile exec -T postgres psql -v ON_ERROR_STOP=1 -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c $query
  if ($LASTEXITCODE -ne 0) {
    throw "Performance check query failed: $query"
  }
}

$overBudgetRaw = docker compose -f $compose --env-file $envFile exec -T postgres psql -t -A -U $env:POSTGRES_USER -d $env:POSTGRES_DB -c "SELECT count(*) FROM pg_stat_statements WHERE mean_exec_time > ${slowMs};"
if ($LASTEXITCODE -ne 0) {
  throw "Failed to compute slow-query over-budget count"
}

$overBudget = [int]($overBudgetRaw.Trim())
if ($overBudget -gt 0) {
  throw "Slow-query budget failed: ${overBudget} statements above ${slowMs}ms mean_exec_time"
}

Write-Host "DB performance budget check passed." -ForegroundColor Green
