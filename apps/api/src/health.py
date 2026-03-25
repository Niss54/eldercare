from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready", "timestamp": datetime.now(UTC).isoformat()}
