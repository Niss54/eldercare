# Load Test Plan (Ramp + Spike + Soak)

## Goal
Validate API baseline resilience and latency SLOs under progressive, burst, and sustained traffic.

## SLO thresholds
- `http_req_failed < 1%`
- `http_req_duration p95 < 500ms`
- `http_req_duration p99 < 1000ms`
- `checks > 99%`

## Profiles
- `ramp`: gradual growth from low to medium/high VUs, then ramp down
- `spike`: sudden traffic burst and controlled drop
- `soak`: sustained steady load to detect drift/leaks

## Endpoints exercised
- `GET /health`
- `GET /api/v1/health`
- `GET /metrics`

## Run
From repo root:

```powershell
./tools/performance/run_load_profiles.ps1
```

Custom target:

```powershell
$env:BASE_URL="http://localhost:8000"
./tools/performance/run_load_profiles.ps1
```

## Artifacts
- Summary exports are written to `tools/performance/reports/<timestamp>/`.
- One JSON summary per profile (`ramp-summary.json`, `spike-summary.json`, `soak-summary.json`).

## Readiness criteria
Mark the roadmap item complete only if all 3 profile runs pass SLO thresholds.
