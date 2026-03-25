import secrets
from datetime import UTC, datetime

from src.modules.notifications.domain.models import Notification, NotificationChannel, NotificationStatus
from src.modules.notifications.service import (
    DeliveryMode,
    NotificationChannel as LegacyChannel,
    NotificationEvent,
    NotificationPriority,
    UserNotificationPreference,
    notification_service,
)


_CHANNEL_MAP = {
    NotificationChannel.email: LegacyChannel.email,
    NotificationChannel.sms: LegacyChannel.sms,
    NotificationChannel.push: LegacyChannel.push,
    NotificationChannel.in_app: LegacyChannel.in_app,
}


class NotificationService:
    """M07.1 application service adapter over the existing notification engine."""

    def send(self, recipient_id: str, type: str, data: dict) -> Notification:
        channels = [NotificationChannel(c) for c in data.get("channels", ["in_app"])]
        legacy_channels = [_CHANNEL_MAP[c] for c in channels]
        message = str(data.get("message") or "")
        dedup_key = data.get("dedup_key")
        mode = DeliveryMode(data.get("mode", DeliveryMode.fanout.value))
        priority = NotificationPriority(data.get("priority", NotificationPriority.routine.value))

        deliveries = notification_service.send_event(
            NotificationEvent(
                event_type=type,
                recipient_user_id=recipient_id,
                template_key=data.get("template_key"),
                variables={k: str(v) for k, v in (data.get("variables") or {}).items()},
                message=message or None,
                channels=legacy_channels,
                priority=priority,
                dedup_key=dedup_key,
                mode=mode,
            )
        )

        status = NotificationStatus.pending
        if deliveries:
            first = deliveries[0]
            if first.status.value == "delivered":
                status = NotificationStatus.delivered
            elif first.status.value == "failed":
                status = NotificationStatus.failed
            else:
                status = NotificationStatus.sent

        return Notification(
            id=deliveries[0].id if deliveries else secrets.token_urlsafe(12),
            recipient_id=recipient_id,
            type=type,
            status=status,
            channels=channels,
            data={k: str(v) for k, v in data.items()},
            created_at=datetime.now(UTC),
        )

    def update_preferences(self, user_id: str, payload: dict) -> UserNotificationPreference:
        channels = [LegacyChannel(c) for c in payload.get("enabled_channels", [LegacyChannel.in_app.value])]
        pref = UserNotificationPreference(
            user_id=user_id,
            enabled_channels=channels,
            quiet_hours_start_utc=payload.get("quiet_hours_start_utc"),
            quiet_hours_end_utc=payload.get("quiet_hours_end_utc"),
            locale=payload.get("locale", "en-US"),
            accessibility_plain_text=bool(payload.get("accessibility_plain_text", False)),
        )
        return notification_service.put_preference(pref)


notification_service_m07 = NotificationService()
