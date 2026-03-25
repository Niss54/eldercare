$ErrorActionPreference = "Stop"

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }
$profiles = @("ramp", "spike", "soak")
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$reportsDir = Join-Path $PSScriptRoot "reports\$timestamp"

$k6Command = Get-Command k6 -ErrorAction SilentlyContinue
$k6Executable = $null
if ($k6Command) {
  $k6Executable = $k6Command.Source
}
if (-not $k6Executable) {
  $candidatePaths = @(
    "C:\Program Files\k6\k6.exe",
    "C:\Program Files (x86)\k6\k6.exe"
  )
  $k6Executable = $candidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $k6Executable) {
  throw "k6 executable not found. Install GrafanaLabs.k6 and ensure k6.exe is on PATH."
}

New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null

Write-Host "Running load profiles against $baseUrl" -ForegroundColor Cyan

foreach ($profile in $profiles) {
  $summaryPath = Join-Path $reportsDir "$profile-summary.json"
  $scriptPath = Join-Path $PSScriptRoot "k6_ramp_spike_soak.js"

  Write-Host "Executing profile: $profile" -ForegroundColor Yellow
  & $k6Executable run --env "BASE_URL=$baseUrl" --env "PROFILE=$profile" --summary-export $summaryPath $scriptPath

  if ($LASTEXITCODE -ne 0) {
    throw "Load profile failed: $profile"
  }
}

Write-Host "Load test suite completed. Reports at: $reportsDir" -ForegroundColor Green
