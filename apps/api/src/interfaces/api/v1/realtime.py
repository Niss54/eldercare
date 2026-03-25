from fastapi import APIRouter, Depends, HTTPException

from src.interfaces.api.v1.auth import _get_claims
from src.modules.realtime.service import realtime_service

router = APIRouter(prefix="/realtime", tags=["realtime"])


def _validate_channel(channel: str) -> None:
    if channel not in {"notifications", "sos"}:
        raise HTTPException(status_code=404, detail="Unknown channel")


@router.get("/events/{channel}")
def list_realtime_events(channel: str, claims: dict = Depends(_get_claims), limit: int = 100, topic: str | None = None):
    _validate_channel(channel)

    events = realtime_service.get_events(channel=channel, limit=limit, topic=topic)
    return {"count": len(events), "items": [event.model_dump() for event in events]}


@router.get("/presence/{channel}")
def channel_presence(channel: str, claims: dict = Depends(_get_claims)):
    _validate_channel(channel)
    return realtime_service.presence(channel=channel)


@router.get("/subscriptions/{channel}")
def channel_subscriptions(channel: str, claims: dict = Depends(_get_claims)):
    _validate_channel(channel)
    return realtime_service.topic_subscriptions(channel=channel)
