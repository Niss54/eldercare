# Quick Start

1. One-command startup:
   - `./infra/scripts/dev-up.ps1`
2. Validate core services:
   - `./infra/scripts/dev-health.ps1`
3. Stop stack:
   - `./infra/scripts/dev-down.ps1`

Manual endpoints:
- API health: http://localhost:8000/health
- Web app: http://localhost:3000
- MinIO console: http://localhost:9001

Prerequisite: Docker Desktop (or equivalent Docker daemon) must be running.

## Local API-only run

1. Create venv and install:
   - `cd apps/api`
   - `python -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1`
   - `pip install -e .[dev]`
2. Run:
   - `uvicorn src.main:app --reload --port 8000`
3. Test:
   - `pytest`
