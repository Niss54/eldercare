import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum

from pydantic import BaseModel

from src.modules.notifications.service import NotificationChannel, NotificationPriority, notification_service


class ReminderStatus(str, Enum):
    pending = "pending"
    dispatched = "dispatched"


class AdherenceStatus(str, Enum):
    taken = "taken"
    skipped = "skipped"
    missed = "missed"


class MedicationSchedule(BaseModel):
    id: str
    subject_user_id: str
    medication_name: str
    dosage: str
    reminder_message: str
    interval_minutes: int = 24 * 60
    next_due_at: datetime
    active: bool = True
    created_at: datetime


class MedicationReminder(BaseModel):
    id: str
    schedule_id: str
    subject_user_id: str
    due_at: datetime
    status: ReminderStatus
    dispatch_key: str
    dispatched_at: datetime | None = None


class MedicationAdherenceRecord(BaseModel):
    id: str
    reminder_id: str
    schedule_id: str
    subject_user_id: str
    status: AdherenceStatus
    recorded_by_user_id: str
    notes: str | None = None
    recorded_at: datetime


class MedicationReminderService:
    def __init__(self):
        self.schedules: dict[str, MedicationSchedule] = {}
        self.reminders: dict[str, MedicationReminder] = {}
        self.adherence_records: dict[str, MedicationAdherenceRecord] = {}
        self.dispatch_history: set[str] = set()

    def create_schedule(
        self,
        subject_user_id: str,
        medication_name: str,
        dosage: str,
        reminder_message: str,
        interval_minutes: int = 24 * 60,
        start_at: datetime | None = None,
    ) -> MedicationSchedule:
        now = datetime.now(UTC)
        schedule = MedicationSchedule(
            id=secrets.token_urlsafe(12),
            subject_user_id=subject_user_id,
            medication_name=medication_name,
            dosage=dosage,
            reminder_message=reminder_message,
            interval_minutes=max(interval_minutes, 1),
            next_due_at=start_at or now,
            created_at=now,
        )
        self.schedules[schedule.id] = schedule
        return schedule

    def queue_due_reminders(self, due_at: datetime | None = None) -> list[MedicationReminder]:
        due_at = due_at or datetime.now(UTC)
        created: list[MedicationReminder] = []
        for schedule in self.schedules.values():
            if not schedule.active:
                continue
            if schedule.next_due_at > due_at:
                continue
            dispatch_key = f"{schedule.id}:{due_at.strftime('%Y%m%d%H%M')}"
            if dispatch_key in self.dispatch_history:
                continue
            reminder = MedicationReminder(
                id=secrets.token_urlsafe(12),
                schedule_id=schedule.id,
                subject_user_id=schedule.subject_user_id,
                due_at=due_at,
                status=ReminderStatus.pending,
                dispatch_key=dispatch_key,
            )
            self.reminders[reminder.id] = reminder
            created.append(reminder)
            schedule.next_due_at = due_at.replace(second=0, microsecond=0)
            schedule.next_due_at = schedule.next_due_at + timedelta(minutes=schedule.interval_minutes)
        return created

    def dispatch_due_reminders(self) -> dict[str, int]:
        dispatched = 0
        for reminder in self.reminders.values():
            if reminder.status != ReminderStatus.pending:
                continue
            schedule = self.schedules.get(reminder.schedule_id)
            if not schedule:
                continue
            if reminder.dispatch_key in self.dispatch_history:
                reminder.status = ReminderStatus.dispatched
                continue
            notification_service.send(
                recipient_user_id=reminder.subject_user_id,
                channels=[NotificationChannel.in_app],
                message=schedule.reminder_message,
                priority=NotificationPriority.routine,
                dedup_key=reminder.dispatch_key,
            )
            reminder.status = ReminderStatus.dispatched
            reminder.dispatched_at = datetime.now(UTC)
            self.dispatch_history.add(reminder.dispatch_key)
            dispatched += 1
        pending = len([r for r in self.reminders.values() if r.status == ReminderStatus.pending])
        return {"dispatched": dispatched, "pending": pending, "total": len(self.reminders)}

    def record_adherence(
        self,
        reminder_id: str,
        status: AdherenceStatus,
        recorded_by_user_id: str,
        notes: str | None = None,
    ) -> MedicationAdherenceRecord | None:
        reminder = self.reminders.get(reminder_id)
        if not reminder:
            return None
        record = MedicationAdherenceRecord(
            id=secrets.token_urlsafe(12),
            reminder_id=reminder.id,
            schedule_id=reminder.schedule_id,
            subject_user_id=reminder.subject_user_id,
            status=status,
            recorded_by_user_id=recorded_by_user_id,
            notes=notes,
            recorded_at=datetime.now(UTC),
        )
        self.adherence_records[record.id] = record
        return record

    def adherence_summary(self, subject_user_id: str) -> dict[str, float | int]:
        records = [r for r in self.adherence_records.values() if r.subject_user_id == subject_user_id]
        taken = len([r for r in records if r.status == AdherenceStatus.taken])
        skipped = len([r for r in records if r.status == AdherenceStatus.skipped])
        missed = len([r for r in records if r.status == AdherenceStatus.missed])
        total = len(records)
        adherence_rate = (taken / total) if total > 0 else 0.0
        return {
            "subject_user_id": subject_user_id,
            "total": total,
            "taken": taken,
            "skipped": skipped,
            "missed": missed,
            "adherence_rate": round(adherence_rate, 4),
        }

    def metrics(self) -> dict[str, int]:
        dispatched = len([r for r in self.reminders.values() if r.status == ReminderStatus.dispatched])
        pending = len([r for r in self.reminders.values() if r.status == ReminderStatus.pending])
        return {
            "schedules": len(self.schedules),
            "reminders_total": len(self.reminders),
            "reminders_dispatched": dispatched,
            "reminders_pending": pending,
            "dispatch_keys": len(self.dispatch_history),
            "adherence_records": len(self.adherence_records),
        }


medication_reminder_service = MedicationReminderService()
