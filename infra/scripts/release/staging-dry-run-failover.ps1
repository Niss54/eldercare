$ErrorActionPreference = "Continue"

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot "../../..")
Set-Location $workspaceRoot

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
$fileStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputDir = "infra/docs/launch-evidence"
$outputPath = Join-Path $outputDir ("staging-dry-run-failover-" + $fileStamp + ".md")

if (-not (Test-Path $outputDir)) {
  New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$results = New-Object System.Collections.Generic.List[object]

function Add-Result {
  param(
    [string]$Area,
    [string]$Check,
    [string]$Status,
    [string]$Evidence,
    [string]$Details
  )

  $results.Add([PSCustomObject]@{
      Area = $Area
      Check = $Check
      Status = $Status
      Evidence = $Evidence
      Details = $Details
    })
}

function Invoke-Check {
  param(
    [string]$Area,
    [string]$Check,
    [string]$Evidence,
    [ScriptBlock]$Script
  )

  try {
    $detail = & $Script
    Add-Result -Area $Area -Check $Check -Status "PASS" -Evidence $Evidence -Details ($detail | Out-String).Trim()
  } catch {
    Add-Result -Area $Area -Check $Check -Status "FAIL" -Evidence $Evidence -Details $_.Exception.Message
  }
}

function Invoke-ExternalCommand {
  param(
    [string]$Command,
    [string[]]$CommandArgs = @()
  )

  $output = & $Command @CommandArgs 2>&1
  $code = $LASTEXITCODE
  if ($code -ne 0) {
    throw "ExitCode=$code | Output=$($output | Out-String)"
  }
  return ($output | Out-String).Trim()
}

Invoke-Check -Area "Staging Dry-Run" -Check "Staging checklist exists" -Evidence "docs/runbooks/staging-signoff-checklist.md" -Script {
  if (-not (Test-Path "docs/runbooks/staging-signoff-checklist.md")) {
    throw "Missing docs/runbooks/staging-signoff-checklist.md"
  }
  "Checklist present"
}

Invoke-Check -Area "Staging Dry-Run" -Check "Staging compose model resolves" -Evidence "docker-compose.staging.yml" -Script {
  Invoke-ExternalCommand -Command "docker" -CommandArgs @("compose", "-f", "docker-compose.staging.yml", "--env-file", ".env", "config") | Out-Null
  "docker compose config succeeded"
}

Invoke-Check -Area "Data Volume" -Check "Production-like load profile report exists" -Evidence "tools/performance/reports" -Script {
  $latest = Get-ChildItem "tools/performance/reports" -Directory -ErrorAction Stop | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($null -eq $latest) {
    throw "No performance report directory found"
  }
  $summary = Join-Path $latest.FullName "ramp-summary.json"
  if (-not (Test-Path $summary)) {
    throw "Missing ramp-summary.json in latest report directory"
  }
  "Found report: $summary"
}

Invoke-Check -Area "Failover Drill" -Check "Failover playbook exists" -Evidence "infra/disaster-recovery/failover-playbooks/api-failover.md" -Script {
  if (-not (Test-Path "infra/disaster-recovery/failover-playbooks/api-failover.md")) {
    throw "Missing API failover playbook"
  }
  "Failover playbook present"
}

Invoke-Check -Area "Failover Drill" -Check "Compose failover rehearsal command path validated" -Evidence "infra/compose/docker-compose.dev.yml" -Script {
  Invoke-ExternalCommand -Command "docker" -CommandArgs @("compose", "-f", "infra/compose/docker-compose.dev.yml", "--env-file", ".env", "ps") | Out-Null
  "Docker compose reachable for rehearsal"
}

Invoke-Check -Area "Failover Drill" -Check "Rollback checklist exists" -Evidence "docs/runbooks/production-deployment-checklist.md" -Script {
  if (-not (Test-Path "docs/runbooks/production-deployment-checklist.md")) {
    throw "Missing production deployment checklist"
  }
  "Rollback checklist present"
}

$passCount = [int](@($results | Where-Object { ($_.Status + "").Trim().ToUpperInvariant() -eq "PASS" }).Count)
$failCount = [int](@($results | Where-Object { ($_.Status + "").Trim().ToUpperInvariant() -eq "FAIL" }).Count)

$lines = @()
$lines += "# Staging Dry-Run and Failover Drill Evidence"
$lines += ""
$lines += "- Generated at: $timestamp"
$lines += "- Workspace: $workspaceRoot"
$lines += "- Passed checks: $passCount"
$lines += "- Failed checks: $failCount"
$lines += ""
$lines += "## Results"
$lines += ""
$lines += "| Area | Check | Status | Evidence | Details |"
$lines += "|---|---|---|---|---|"

foreach ($item in $results) {
  $safeDetails = ($item.Details -replace "\|", "/" -replace "\r?\n", " ").Trim()
  $lines += "| $($item.Area) | $($item.Check) | $($item.Status) | $($item.Evidence) | $safeDetails |"
}

$lines += ""
$lines += "## Completion Guidance"
$lines += ""
$lines += "- All checks must pass before marking staging dry-run and failover drill as complete."
$lines += "- If Docker checks fail, start Docker daemon and rerun this script."

Set-Content -Path $outputPath -Value $lines -Encoding UTF8

Write-Host "Staging dry-run evidence report generated: $outputPath" -ForegroundColor Green
if ($failCount -gt 0) {
  Write-Host "Some checks failed. Resolve blockers and rerun." -ForegroundColor Yellow
  exit 2
}
