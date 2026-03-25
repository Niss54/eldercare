from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.api.v1.auth import _get_claims
from src.modules.notifications.application.services import notification_service_m07
from src.modules.notifications.service import (
    DeliveryMode,
    NotificationChannel,
    NotificationEvent,
    NotificationPriority,
    NotificationTemplate,
    UserNotificationPreference,
    notification_service,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class SendNotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_user_id: str
    message: str = Field(min_length=2)
    channels: list[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.routine
    dedup_key: str | None = None
    mode: DeliveryMode = DeliveryMode.fanout


class SendEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=3)
    recipient_user_id: str
    template_key: str | None = None
    variables: dict[str, str] = Field(default_factory=dict)
    message: str | None = None
    channels: list[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.routine
    dedup_key: str | None = None
    mode: DeliveryMode = DeliveryMode.fanout


class PutTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=2)
    channel: NotificationChannel
    locale: str = "en-US"
    priority: NotificationPriority = NotificationPriority.routine
    subject_template: str | None = None
    body_template: str = Field(min_length=2)


class PutPreferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled_channels: list[NotificationChannel]
    quiet_hours_start_utc: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_end_utc: int | None = Field(default=None, ge=0, le=23)
    locale: str = "en-US"
    accessibility_plain_text: bool = False


class ProviderCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str
    provider_name: str
    external_status: str
    payload: dict[str, str] = Field(default_factory=dict)


@router.post("/send")
def send_notification(payload: SendNotificationRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "notification:send" not in permissions and claims.get("sub") != payload.recipient_user_id:
        raise HTTPException(status_code=403, detail="Missing permission: notification:send")

    deliveries = notification_service.send(
        recipient_user_id=payload.recipient_user_id,
        channels=payload.channels,
        message=payload.message,
        priority=payload.priority,
        dedup_key=payload.dedup_key,
        mode=payload.mode,
    )
    return {"count": len(deliveries), "items": [d.model_dump() for d in deliveries]}


@router.post("/events/send")
def send_event(payload: SendEventRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "notification:send" not in permissions and claims.get("sub") != payload.recipient_user_id:
        raise HTTPException(status_code=403, detail="Missing permission: notification:send")

    deliveries = notification_service.send_event(
        NotificationEvent(
            event_type=payload.event_type,
            recipient_user_id=payload.recipient_user_id,
            template_key=payload.template_key,
            variables=payload.variables,
            message=payload.message,
            channels=payload.channels,
            priority=payload.priority,
            dedup_key=payload.dedup_key,
            mode=payload.mode,
        )
    )
    return {"count": len(deliveries), "items": [d.model_dump() for d in deliveries]}


@router.put("/templates/{template_key}")
def put_template(template_key: str, payload: PutTemplateRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "notification:send" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: notification:send")

    template = notification_service.put_template(
        NotificationTemplate(
            key=template_key,
            channel=payload.channel,
            locale=payload.locale,
            priority=payload.priority,
            subject_template=payload.subject_template,
            body_template=payload.body_template,
        )
    )
    return template.model_dump()


@router.get("/templates")
def list_templates(claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "notification:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: notification:read")
    templates = notification_service.list_templates()
    return {"count": len(templates), "items": [t.model_dump() for t in templates]}


@router.put("/preferences/{user_id}")
def put_preference(user_id: str, payload: PutPreferenceRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if claims.get("sub") != user_id and "notification:send" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission to manage preferences")

    pref = notification_service_m07.update_preferences(
        user_id=user_id,
        payload={
            "enabled_channels": [c.value for c in payload.enabled_channels],
            "quiet_hours_start_utc": payload.quiet_hours_start_utc,
            "quiet_hours_end_utc": payload.quiet_hours_end_utc,
            "locale": payload.locale,
            "accessibility_plain_text": payload.accessibility_plain_text,
        },
    )
    return pref.model_dump()


@router.get("/preferences/{user_id}")
def get_preference(user_id: str, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if claims.get("sub") != user_id and "notification:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission to read preferences")
    return notification_service.get_preference(user_id).model_dump()


@router.post("/provider-callback")
def provider_callback(payload: ProviderCallbackRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "notification:send" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: notification:send")
    callback = notification_service.provider_callback(
        delivery_id=payload.delivery_id,
        provider_name=payload.provider_name,
        external_status=payload.external_status,
        payload=payload.payload,
    )
    return callback.model_dump()


@router.get("/deliveries")
def list_deliveries(recipient_user_id: str | None = None, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "notification:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: notification:read")

    if recipient_user_id is None and "notification:send" not in permissions:
        recipient_user_id = claims["sub"]
    deliveries = notification_service.list_deliveries(recipient_user_id=recipient_user_id)
    return {"count": len(deliveries), "items": [d.model_dump() for d in deliveries]}


@router.get("/metrics")
def notification_metrics(claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "notification:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: notification:read")
    return notification_service.metrics()
