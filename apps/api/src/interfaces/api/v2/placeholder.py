from datetime import UTC, datetime
from fastapi import APIRouter

router = APIRouter(prefix="/meta", tags=["v2-placeholder"])


@router.get("/status")
def status() -> dict[str, str]:
    return {
        "version": "v2",
        "status": "placeholder",
        "timestamp": datetime.now(UTC).isoformat(),
    }
