param(
  [Parameter(Mandatory = $true)]
  [string]$TaskName,
  [Parameter(Mandatory = $true)]
  [string]$PayloadJson
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
  throw "Missing .env file"
}

# Payload must include args and kwargs arrays/objects for replay.
$payload = $PayloadJson | ConvertFrom-Json
if ($null -eq $payload.args -or $null -eq $payload.kwargs) {
  throw "PayloadJson must contain args and kwargs"
}

$python = Resolve-Path "$PSScriptRoot/../../../.venv/Scripts/python.exe"
$script = @"
from src.celery_app import celery_app
import json

payload = json.loads(r'''$PayloadJson''')
result = celery_app.send_task(
    '$TaskName',
    args=payload.get('args', []),
    kwargs=payload.get('kwargs', {}),
)
print(result.id)
"@

Set-Location "apps/worker"
& $python.Path -c $script
Write-Host "Replay dispatched for task: $TaskName" -ForegroundColor Green
