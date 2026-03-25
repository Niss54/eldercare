from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.interfaces.api.v1.auth import _get_claims
from src.interfaces.api.v1.contracts import list_response, success_response
from src.metrics import metrics_recorder
from src.modules.medication.application.services import medication_engine_service
from src.modules.medication.domain.models import AdherenceStatus
from src.modules.medication_reminders.service import medication_reminder_service

router = APIRouter(prefix="/medication", tags=["medication"])


class MedicationScheduleCreateRequest(BaseModel):
    subject_user_id: str
    medication_name: str = Field(min_length=2)
    dosage: str = Field(min_length=1)
    reminder_message: str = Field(min_length=3)
    interval_minutes: int = Field(default=24 * 60, ge=1)
    start_at: datetime | None = None


class RecordAdherenceRequest(BaseModel):
    status: AdherenceStatus
    notes: str | None = None


@router.post("/schedules")
def create_schedule(payload: MedicationScheduleCreateRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "medication:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: medication:manage")

    schedule = medication_engine_service.create_schedule(
        subject_user_id=payload.subject_user_id,
        medication_name=payload.medication_name,
        dosage=payload.dosage,
        reminder_message=payload.reminder_message,
        interval_minutes=payload.interval_minutes,
        start_at=payload.start_at,
    )
    return success_response(data=schedule.model_dump(), message="medication.schedule.created")


@router.post("/queue-due")
def queue_due_reminders(claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "medication:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: medication:manage")

    reminders = medication_reminder_service.queue_due_reminders(due_at=datetime.now(UTC))
    return list_response(
        items=[r.model_dump() for r in reminders],
        page=1,
        page_size=len(reminders) if reminders else 0,
        total=len(reminders),
        message="medication.queue_due",
    )


@router.post("/dispatch-due")
def dispatch_due_reminders(claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "medication:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: medication:manage")

    return success_response(
        data=medication_reminder_service.dispatch_due_reminders(),
        message="medication.dispatch_due",
    )


@router.get("/metrics")
def medication_metrics(claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "medication:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: medication:read")
    return success_response(data=medication_reminder_service.metrics(), message="medication.metrics")


@router.post("/reminders/{reminder_id}/adherence")
def record_adherence(reminder_id: str, payload: RecordAdherenceRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "medication:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: medication:manage")

    record = medication_engine_service.record_adherence(
        reminder_id=reminder_id,
        status=payload.status,
        recorded_by_user_id=claims["sub"],
        notes=payload.notes,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Medication reminder not found")
    metrics_recorder.observe_medication_adherence(payload.status.value)
    return success_response(data=record.model_dump(), message="medication.adherence.recorded")


@router.get("/adherence/{subject_user_id}")
def medication_adherence_summary(subject_user_id: str, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "medication:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: medication:read")
    return success_response(
        data=medication_engine_service.adherence_summary(subject_user_id=subject_user_id),
        message="medication.adherence.summary",
    )
