import hashlib
import secrets
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field

from src.modules.realtime.service import realtime_service


class NotificationChannel(str, Enum):
    email = "email"
    sms = "sms"
    push = "push"
    in_app = "in_app"


class NotificationPriority(str, Enum):
    routine = "routine"
    urgent = "urgent"
    critical = "critical"


class DeliveryStatus(str, Enum):
    queued = "queued"
    sent = "sent"
    delivered = "delivered"
    failed = "failed"
    suppressed = "suppressed"


class DeliveryMode(str, Enum):
    fanout = "fanout"
    fallback = "fallback"


class NotificationTemplate(BaseModel):
    key: str
    channel: NotificationChannel
    locale: str
    priority: NotificationPriority = NotificationPriority.routine
    subject_template: str | None = None
    body_template: str


class UserNotificationPreference(BaseModel):
    user_id: str
    enabled_channels: list[NotificationChannel]
    quiet_hours_start_utc: int | None = None
    quiet_hours_end_utc: int | None = None
    locale: str = "en-US"
    accessibility_plain_text: bool = False


class NotificationEvent(BaseModel):
    event_type: str
    recipient_user_id: str
    template_key: str | None = None
    variables: dict[str, str] = Field(default_factory=dict)
    message: str | None = None
    channels: list[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.routine
    dedup_key: str | None = None
    mode: DeliveryMode = DeliveryMode.fanout


class NotificationDelivery(BaseModel):
    id: str
    event_id: str
    recipient_user_id: str
    channel: NotificationChannel
    message: str
    priority: NotificationPriority
    status: DeliveryStatus
    dedup_key: str | None = None
    provider_name: str
    provider_message_id: str | None = None
    fallback_from_channel: NotificationChannel | None = None
    created_at: datetime
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None


class ProviderCallbackEvent(BaseModel):
    delivery_id: str
    provider_name: str
    external_status: str
    payload: dict[str, str] = {}
    received_at: datetime


@dataclass(slots=True)
class ProviderSendResult:
    success: bool
    provider_name: str
    provider_message_id: str | None = None
    response_code: str | None = None
    error_message: str | None = None


class NotificationProvider(Protocol):
    channel: NotificationChannel
    provider_name: str

    def send(self, recipient_user_id: str, message: str, priority: NotificationPriority) -> ProviderSendResult:
        ...


class EmailProvider:
    channel = NotificationChannel.email
    provider_name = "email-provider"

    def send(self, recipient_user_id: str, message: str, priority: NotificationPriority) -> ProviderSendResult:
        return ProviderSendResult(success=True, provider_name=self.provider_name, provider_message_id=secrets.token_urlsafe(8))


class SmsProvider:
    channel = NotificationChannel.sms
    provider_name = "sms-provider"

    def send(self, recipient_user_id: str, message: str, priority: NotificationPriority) -> ProviderSendResult:
        if "__force_fail__" in message:
            return ProviderSendResult(success=False, provider_name=self.provider_name, response_code="503", error_message="provider down")
        return ProviderSendResult(success=True, provider_name=self.provider_name, provider_message_id=secrets.token_urlsafe(8))


class PushProvider:
    channel = NotificationChannel.push
    provider_name = "push-provider"

    def send(self, recipient_user_id: str, message: str, priority: NotificationPriority) -> ProviderSendResult:
        return ProviderSendResult(success=True, provider_name=self.provider_name, provider_message_id=secrets.token_urlsafe(8))


class InAppProvider:
    channel = NotificationChannel.in_app
    provider_name = "in-app-provider"

    def send(self, recipient_user_id: str, message: str, priority: NotificationPriority) -> ProviderSendResult:
        return ProviderSendResult(success=True, provider_name=self.provider_name, provider_message_id=secrets.token_urlsafe(8))


class NotificationService:
    def __init__(self):
        self.deliveries: list[NotificationDelivery] = []
        self.callbacks: list[ProviderCallbackEvent] = []
        self.templates: dict[str, NotificationTemplate] = {
            "medication_due": NotificationTemplate(
                key="medication_due",
                channel=NotificationChannel.in_app,
                locale="en-US",
                priority=NotificationPriority.routine,
                body_template="Medication reminder: {message}",
            ),
            "sos_triggered": NotificationTemplate(
                key="sos_triggered",
                channel=NotificationChannel.sms,
                locale="en-US",
                priority=NotificationPriority.critical,
                body_template="SOS incident {incident_id} requires acknowledgement",
            ),
        }
        self.preferences: dict[str, UserNotificationPreference] = {}
        self.providers: dict[NotificationChannel, NotificationProvider] = {
            NotificationChannel.email: EmailProvider(),
            NotificationChannel.sms: SmsProvider(),
            NotificationChannel.push: PushProvider(),
            NotificationChannel.in_app: InAppProvider(),
        }
        self.throttle_history: dict[str, deque[datetime]] = defaultdict(deque)
        self.dedup_history: dict[str, datetime] = {}
        self.suppression_rules: list[str] = ["spam", "test-suppress"]
        self.throttle_limit_per_minute = 20
        self.dedup_window_seconds = 180

    def _is_quiet_hours(self, pref: UserNotificationPreference, at: datetime) -> bool:
        if pref.quiet_hours_start_utc is None or pref.quiet_hours_end_utc is None:
            return False
        hour = at.hour
        start = pref.quiet_hours_start_utc
        end = pref.quiet_hours_end_utc
        if start == end:
            return False
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    def _is_suppressed_message(self, message: str) -> bool:
        lowered = message.lower()
        return any(token in lowered for token in self.suppression_rules)

    def _throttle_allowed(self, user_id: str, channel: NotificationChannel, now: datetime) -> bool:
        key = f"{user_id}:{channel.value}"
        events = self.throttle_history[key]
        while events and (now - events[0]).total_seconds() > 60:
            events.popleft()
        if len(events) >= self.throttle_limit_per_minute:
            return False
        events.append(now)
        return True

    def _dedup_allowed(self, dedup_key: str, now: datetime) -> bool:
        previous = self.dedup_history.get(dedup_key)
        if previous and (now - previous).total_seconds() <= self.dedup_window_seconds:
            return False
        self.dedup_history[dedup_key] = now
        return True

    def _resolve_preference(self, user_id: str) -> UserNotificationPreference:
        return self.preferences.get(
            user_id,
            UserNotificationPreference(
                user_id=user_id,
                enabled_channels=[
                    NotificationChannel.email,
                    NotificationChannel.sms,
                    NotificationChannel.push,
                    NotificationChannel.in_app,
                ],
                locale="en-US",
                accessibility_plain_text=False,
            ),
        )

    def _render_message(self, event: NotificationEvent, pref: UserNotificationPreference) -> str:
        if event.template_key and event.template_key in self.templates:
            template = self.templates[event.template_key]
            body = template.body_template.format(**event.variables)
        else:
            body = event.message or ""

        if pref.accessibility_plain_text:
            body = f"ACCESSIBLE NOTICE: {body}"

        if pref.locale.lower().startswith("hi"):
            body = f"[HI] {body}"
        return body

    def put_template(self, template: NotificationTemplate) -> NotificationTemplate:
        self.templates[template.key] = template
        return template

    def list_templates(self) -> list[NotificationTemplate]:
        return sorted(self.templates.values(), key=lambda t: t.key)

    def put_preference(self, pref: UserNotificationPreference) -> UserNotificationPreference:
        self.preferences[pref.user_id] = pref
        return pref

    def get_preference(self, user_id: str) -> UserNotificationPreference:
        return self._resolve_preference(user_id)

    def send_event(self, event: NotificationEvent) -> list[NotificationDelivery]:
        now = datetime.now(UTC)
        pref = self._resolve_preference(event.recipient_user_id)
        message = self._render_message(event, pref)
        channels = [channel for channel in event.channels if channel in pref.enabled_channels]
        if not channels:
            channels = [NotificationChannel.in_app]

        dedup_key = event.dedup_key or hashlib.sha256(
            f"{event.recipient_user_id}|{event.event_type}|{event.template_key}|{message}|{','.join(c.value for c in channels)}".encode(
                "utf-8"
            )
        ).hexdigest()[:20]

        if not self._dedup_allowed(dedup_key, now):
            delivery = NotificationDelivery(
                id=secrets.token_urlsafe(12),
                event_id=event.event_type,
                recipient_user_id=event.recipient_user_id,
                channel=channels[0],
                message=message,
                priority=event.priority,
                status=DeliveryStatus.suppressed,
                dedup_key=dedup_key,
                provider_name="dedup-guard",
                created_at=now,
            )
            self.deliveries.append(delivery)
            return [delivery]

        if self._is_suppressed_message(message):
            delivery = NotificationDelivery(
                id=secrets.token_urlsafe(12),
                event_id=event.event_type,
                recipient_user_id=event.recipient_user_id,
                channel=channels[0],
                message=message,
                priority=event.priority,
                status=DeliveryStatus.suppressed,
                dedup_key=dedup_key,
                provider_name="suppression-rule",
                created_at=now,
            )
            self.deliveries.append(delivery)
            return [delivery]

        if self._is_quiet_hours(pref, now) and event.priority != NotificationPriority.critical:
            delivery = NotificationDelivery(
                id=secrets.token_urlsafe(12),
                event_id=event.event_type,
                recipient_user_id=event.recipient_user_id,
                channel=channels[0],
                message=message,
                priority=event.priority,
                status=DeliveryStatus.suppressed,
                dedup_key=dedup_key,
                provider_name="quiet-hours",
                created_at=now,
            )
            self.deliveries.append(delivery)
            return [delivery]

        created: list[NotificationDelivery] = []
        previous_channel: NotificationChannel | None = None

        for channel in channels:
            if not self._throttle_allowed(event.recipient_user_id, channel, now):
                delivery = NotificationDelivery(
                    id=secrets.token_urlsafe(12),
                    event_id=event.event_type,
                    recipient_user_id=event.recipient_user_id,
                    channel=channel,
                    message=message,
                    priority=event.priority,
                    status=DeliveryStatus.suppressed,
                    dedup_key=dedup_key,
                    provider_name="throttle",
                    created_at=now,
                    fallback_from_channel=previous_channel,
                )
                self.deliveries.append(delivery)
                created.append(delivery)
                continue

            provider = self.providers[channel]
            result = provider.send(event.recipient_user_id, message, event.priority)
            delivery = NotificationDelivery(
                id=secrets.token_urlsafe(12),
                event_id=event.event_type,
                recipient_user_id=event.recipient_user_id,
                channel=channel,
                message=message,
                priority=event.priority,
                status=DeliveryStatus.delivered if result.success else DeliveryStatus.failed,
                dedup_key=dedup_key,
                provider_name=result.provider_name,
                provider_message_id=result.provider_message_id,
                fallback_from_channel=previous_channel,
                created_at=now,
                sent_at=now,
                delivered_at=now if result.success else None,
                failed_at=now if not result.success else None,
            )
            self.deliveries.append(delivery)
            created.append(delivery)

            realtime_service.publish(
                channel="notifications",
                event_type="notification.delivered" if result.success else "notification.failed",
                payload={
                    "delivery_id": delivery.id,
                    "recipient_user_id": event.recipient_user_id,
                    "channel": channel.value,
                    "priority": event.priority.value,
                    "status": delivery.status.value,
                },
            )

            if result.success and event.mode == DeliveryMode.fallback:
                break
            if result.success and event.mode == DeliveryMode.fanout:
                previous_channel = channel
                continue
            previous_channel = channel

        return created

    def send(
        self,
        recipient_user_id: str,
        channels: list[NotificationChannel],
        message: str,
        priority: NotificationPriority,
        dedup_key: str | None = None,
        mode: DeliveryMode = DeliveryMode.fanout,
    ) -> list[NotificationDelivery]:
        return self.send_event(
            NotificationEvent(
                event_type="manual.send",
                recipient_user_id=recipient_user_id,
                channels=channels,
                message=message,
                priority=priority,
                dedup_key=dedup_key,
                mode=mode,
            )
        )

    def provider_callback(self, delivery_id: str, provider_name: str, external_status: str, payload: dict[str, str]) -> ProviderCallbackEvent:
        callback = ProviderCallbackEvent(
            delivery_id=delivery_id,
            provider_name=provider_name,
            external_status=external_status,
            payload=payload,
            received_at=datetime.now(UTC),
        )
        self.callbacks.append(callback)
        for delivery in self.deliveries:
            if delivery.id != delivery_id:
                continue
            if external_status.lower() in {"delivered", "ok", "success"}:
                delivery.status = DeliveryStatus.delivered
                delivery.delivered_at = callback.received_at
                delivery.failed_at = None
            elif external_status.lower() in {"failed", "error", "bounced"}:
                delivery.status = DeliveryStatus.failed
                delivery.failed_at = callback.received_at
            break
        return callback

    def list_deliveries(self, recipient_user_id: str | None = None) -> list[NotificationDelivery]:
        if recipient_user_id is None:
            return list(self.deliveries)
        return [d for d in self.deliveries if d.recipient_user_id == recipient_user_id]

    def metrics(self) -> dict[str, int]:
        delivered = len([d for d in self.deliveries if d.status == DeliveryStatus.delivered])
        failed = len([d for d in self.deliveries if d.status == DeliveryStatus.failed])
        suppressed = len([d for d in self.deliveries if d.status == DeliveryStatus.suppressed])
        return {
            "total": len(self.deliveries),
            "delivered": delivered,
            "failed": failed,
            "suppressed": suppressed,
            "callbacks": len(self.callbacks),
        }


notification_service = NotificationService()
