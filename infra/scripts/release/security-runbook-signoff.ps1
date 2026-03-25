$ErrorActionPreference = "Continue"

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot "../../..")
Set-Location $workspaceRoot

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
$fileStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputDir = "infra/docs/launch-evidence"
$outputPath = Join-Path $outputDir ("security-runbook-signoff-" + $fileStamp + ".md")

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

Invoke-Check -Area "Security Docs" -Check "Security architecture doc exists" -Evidence "security.md" -Script {
  if (-not (Test-Path "security.md")) {
    throw "Missing required file: security.md"
  }
  "Present"
}

Invoke-Check -Area "Security Docs" -Check "Incident response runbook exists" -Evidence "docs/runbooks/incident-response.md" -Script {
  if (-not (Test-Path "docs/runbooks/incident-response.md")) {
    throw "Missing required file: docs/runbooks/incident-response.md"
  }
  "Present"
}

Invoke-Check -Area "Runbooks" -Check "On-call runbook exists" -Evidence "docs/runbooks/on-call.md" -Script {
  if (-not (Test-Path "docs/runbooks/on-call.md")) {
    throw "Missing required file: docs/runbooks/on-call.md"
  }
  "Present"
}

Invoke-Check -Area "Runbooks" -Check "Rollback checklist exists" -Evidence "docs/runbooks/production-deployment-checklist.md" -Script {
  if (-not (Test-Path "docs/runbooks/production-deployment-checklist.md")) {
    throw "Missing required file: docs/runbooks/production-deployment-checklist.md"
  }
  "Present"
}

Invoke-Check -Area "Security Controls" -Check "Security middleware module present" -Evidence "apps/api/src/core/security.py" -Script {
  if (-not (Test-Path "apps/api/src/core/security.py")) {
    throw "Missing required file: apps/api/src/core/security.py"
  }
  "Present"
}

Invoke-Check -Area "Security Controls" -Check "Secret-manager guardrails present" -Evidence "apps/api/src/core/settings.py" -Script {
  $settings = Get-Content "apps/api/src/core/settings.py" -Raw
  if ($settings -notmatch "secret_manager_provider") {
    throw "secret_manager_provider setting not found"
  }
  if ($settings -notmatch "must not be 'env' for non-local environments") {
    throw "non-local secret manager guardrail not found"
  }
  "Secret-manager guardrails detected"
}

Invoke-Check -Area "Runbook Rehearsal" -Check "On-call escalation paths documented" -Evidence "docs/runbooks/on-call.md" -Script {
  $oncall = Get-Content "docs/runbooks/on-call.md" -Raw
  if ($oncall -notmatch "Primary") {
    throw "Primary on-call path missing"
  }
  if ($oncall -notmatch "Secondary") {
    throw "Secondary on-call path missing"
  }
  "Primary and secondary escalation documented"
}

Invoke-Check -Area "Runbook Rehearsal" -Check "Incident severity matrix documented" -Evidence "docs/runbooks/incident-response.md" -Script {
  $incident = Get-Content "docs/runbooks/incident-response.md" -Raw
  if ($incident -notmatch "SEV-1") {
    throw "SEV-1 not found"
  }
  if ($incident -notmatch "SEV-2") {
    throw "SEV-2 not found"
  }
  "Incident severity matrix present"
}

$passCount = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failCount = ($results | Where-Object { $_.Status -eq "FAIL" }).Count

$lines = @()
$lines += "# Security and Incident Runbook Signoff Evidence"
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
$lines += "## Signoff"
$lines += ""
$lines += "| Role | Name | Date | Decision |"
$lines += "|---|---|---|---|"
$lines += "| Security Lead |  |  |  |"
$lines += "| Incident Commander (On-call) |  |  |  |"
$lines += "| Platform Lead |  |  |  |"

Set-Content -Path $outputPath -Value $lines -Encoding UTF8

Write-Host "Security runbook signoff evidence report generated: $outputPath" -ForegroundColor Green
if ($failCount -gt 0) {
  Write-Host "Some checks failed. Resolve blockers before final signoff." -ForegroundColor Yellow
  exit 2
}
