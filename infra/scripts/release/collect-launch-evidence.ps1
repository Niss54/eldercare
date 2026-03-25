$ErrorActionPreference = "Continue"

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot "../../..")
Set-Location $workspaceRoot

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss K"
$fileStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputDir = "infra/docs/launch-evidence"
$outputPath = Join-Path $outputDir ("launch-evidence-" + $fileStamp + ".md")

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

# Staging signoff evidence
Invoke-Check -Area "Staging Signoff" -Check "Staging runbook checklist exists" -Evidence "docs/runbooks/staging-signoff-checklist.md" -Script {
  if (-not (Test-Path "docs/runbooks/staging-signoff-checklist.md")) {
    throw "Missing docs/runbooks/staging-signoff-checklist.md"
  }
  "Runbook present"
}

Invoke-Check -Area "Staging Signoff" -Check "Compose staging config dry-run" -Evidence "docker-compose.staging.yml" -Script {
  Invoke-ExternalCommand -Command "docker" -CommandArgs @("compose", "-f", "docker-compose.staging.yml", "--env-file", ".env", "config") | Out-Null
  "docker compose config succeeded"
}

Invoke-Check -Area "Staging Signoff" -Check "Staging stack health probe" -Evidence "infra/scripts/dev-health.ps1" -Script {
  Invoke-ExternalCommand -Command "powershell" -CommandArgs @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "infra/scripts/dev-health.ps1") | Out-Null
  "dev-health checks succeeded"
}

# Production dry-run evidence
Invoke-Check -Area "Production Dry-Run" -Check "Compose production config dry-run" -Evidence "docker-compose.prod.yml" -Script {
  Invoke-ExternalCommand -Command "docker" -CommandArgs @("compose", "-f", "docker-compose.prod.yml", "--env-file", ".env", "config") | Out-Null
  "docker compose config succeeded"
}

Invoke-Check -Area "Production Dry-Run" -Check "Kubernetes client available" -Evidence "kubectl client" -Script {
  Invoke-ExternalCommand -Command "kubectl" -CommandArgs @("version", "--client", "--output=yaml")
}

Invoke-Check -Area "Production Dry-Run" -Check "Helm client available" -Evidence "helm client" -Script {
  Invoke-ExternalCommand -Command "helm" -CommandArgs @("version")
}

# Secrets injection verification evidence
Invoke-Check -Area "Secrets Injection" -Check "Secrets setup script exists" -Evidence "infra/scripts/setup-secrets.sh" -Script {
  if (-not (Test-Path "infra/scripts/setup-secrets.sh")) {
    throw "Missing infra/scripts/setup-secrets.sh"
  }
  "Script present"
}

Invoke-Check -Area "Secrets Injection" -Check "Secrets script shell syntax valid" -Evidence "infra/scripts/setup-secrets.sh" -Script {
  Invoke-ExternalCommand -Command "bash" -CommandArgs @("-n", "infra/scripts/setup-secrets.sh")
  "bash syntax check passed"
}

Invoke-Check -Area "Secrets Injection" -Check "AWS identity available for secret operations" -Evidence "aws sts get-caller-identity" -Script {
  $identity = Invoke-ExternalCommand -Command "aws" -CommandArgs @("sts", "get-caller-identity", "--output", "json")
  if (-not $identity) {
    throw "Empty identity response"
  }
  "AWS caller identity resolved"
}

$passCount = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failCount = ($results | Where-Object { $_.Status -eq "FAIL" }).Count

$lines = @()
$lines += "# Launch Execution Evidence"
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
$lines += "- Treat this report as environment evidence for launch checklist execution."
$lines += "- Remaining FAIL items must be resolved before final launch sign-off."

Set-Content -Path $outputPath -Value $lines -Encoding UTF8

Write-Host "Launch evidence report generated: $outputPath" -ForegroundColor Green
if ($failCount -gt 0) {
  Write-Host "Some checks failed. Review the report before marking full sign-off." -ForegroundColor Yellow
}
