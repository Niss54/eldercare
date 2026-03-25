from datetime import UTC, datetime

from src.modules.medication.domain.models import AdherenceEvent, AdherenceStatus, ReminderSchedule
from src.modules.medication_reminders.service import (
    AdherenceStatus as LegacyAdherenceStatus,
    medication_reminder_service,
)


class MedicationEngineService:
    """M08.1 scheduling and adherence adapter over medication_reminders service."""

    def create_schedule(
        self,
        *,
        subject_user_id: str,
        medication_name: str,
        dosage: str,
        reminder_message: str,
        interval_minutes: int = 24 * 60,
        start_at: datetime | None = None,
    ) -> ReminderSchedule:
        schedule = medication_reminder_service.create_schedule(
            subject_user_id=subject_user_id,
            medication_name=medication_name,
            dosage=dosage,
            reminder_message=reminder_message,
            interval_minutes=interval_minutes,
            start_at=start_at,
        )
        return ReminderSchedule(
            id=schedule.id,
            subject_user_id=schedule.subject_user_id,
            medication_name=schedule.medication_name,
            dosage=schedule.dosage,
            reminder_message=schedule.reminder_message,
            interval_minutes=schedule.interval_minutes,
            next_due_at=schedule.next_due_at,
            active=schedule.active,
            created_at=schedule.created_at,
        )

    def queue_and_dispatch_due(self, *, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.now(UTC)
        medication_reminder_service.queue_due_reminders(due_at=now)
        return medication_reminder_service.dispatch_due_reminders()

    def record_adherence(
        self,
        *,
        reminder_id: str,
        status: AdherenceStatus,
        recorded_by_user_id: str,
        notes: str | None = None,
    ) -> AdherenceEvent | None:
        record = medication_reminder_service.record_adherence(
            reminder_id=reminder_id,
            status=LegacyAdherenceStatus(status.value),
            recorded_by_user_id=recorded_by_user_id,
            notes=notes,
        )
        if not record:
            return None
        return AdherenceEvent(
            id=record.id,
            reminder_id=record.reminder_id,
            schedule_id=record.schedule_id,
            subject_user_id=record.subject_user_id,
            status=AdherenceStatus(record.status.value),
            recorded_by_user_id=record.recorded_by_user_id,
            notes=record.notes,
            recorded_at=record.recorded_at,
        )

    def adherence_summary(self, *, subject_user_id: str) -> dict[str, float | int]:
        return medication_reminder_service.adherence_summary(subject_user_id=subject_user_id)


medication_engine_service = MedicationEngineService()
