from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class AdherenceStatus(str, Enum):
    taken = "taken"
    skipped = "skipped"
    missed = "missed"


class ReminderSchedule(BaseModel):
    id: str
    subject_user_id: str
    medication_name: str
    dosage: str
    reminder_message: str
    interval_minutes: int = Field(default=24 * 60, ge=1)
    next_due_at: datetime
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AdherenceEvent(BaseModel):
    id: str
    reminder_id: str
    schedule_id: str
    subject_user_id: str
    status: AdherenceStatus
    recorded_by_user_id: str
    notes: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
