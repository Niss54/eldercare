from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class NotificationStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    delivered = "delivered"
    failed = "failed"


class NotificationChannel(str, Enum):
    email = "email"
    sms = "sms"
    push = "push"
    in_app = "in_app"


class Notification(BaseModel):
    id: str
    recipient_id: str
    type: str
    status: NotificationStatus
    channels: list[NotificationChannel]
    data: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
