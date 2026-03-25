$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
  throw "Missing .env file"
}

$python = Resolve-Path "$PSScriptRoot/../../../.venv/Scripts/python.exe"
$workerRoot = Resolve-Path "$PSScriptRoot/../../../apps/worker"

$script = @"
import json
import time

from src.celery_app import celery_app


def metric(metrics_payload, key):
    return int(metrics_payload.get("counters", {}).get(key, 0))


before = celery_app.send_task("scheduler.metrics", kwargs={"queue_lag_seconds": 45.0}).get(timeout=20)

result = celery_app.send_task("scheduler.force_retry_then_fail", kwargs={"token": "launch-validation"})
try:
    result.get(timeout=45)
except Exception:
    pass

time.sleep(2)
after = celery_app.send_task("scheduler.metrics", kwargs={"queue_lag_seconds": 90.0}).get(timeout=20)

report = {
    "before": before,
    "after": after,
    "validation": {
        "retry_incremented": metric(after, "task_retries_total") > metric(before, "task_retries_total"),
        "failure_incremented": metric(after, "task_failures_total") > metric(before, "task_failures_total"),
        "dead_letter_incremented": metric(after, "dead_letter_events_total") > metric(before, "dead_letter_events_total"),
        "queue_lag_observed": float(after.get("queue_lag_seconds", 0.0)) >= 90.0,
    },
}

passed = all(report["validation"].values())
print(json.dumps(report, indent=2))
print("VALIDATION_PASS" if passed else "VALIDATION_FAIL")

if not passed:
    raise SystemExit(2)
"@

Set-Location $workerRoot
$env:PYTHONPATH = $workerRoot
$tmpScript = [System.IO.Path]::GetTempFileName() + ".py"
Set-Content -Path $tmpScript -Value $script -Encoding UTF8

& $python.Path $tmpScript
if ($LASTEXITCODE -ne 0) {
    Remove-Item $tmpScript -ErrorAction SilentlyContinue
    throw "Queue backpressure validation failed (python exit code: $LASTEXITCODE)"
}

Remove-Item $tmpScript -ErrorAction SilentlyContinue
Write-Host "Queue backpressure and retry/dead-letter validation passed." -ForegroundColor Green
