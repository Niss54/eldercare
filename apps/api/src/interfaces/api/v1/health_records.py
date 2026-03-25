from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.api.v1.auth import _get_claims
from src.interfaces.api.v1.contracts import list_response, success_response
from src.middleware.consent import require_consent
from src.modules.audit_logging.store import audit_log_store
from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.health.application.services import health_record_service_m05
from src.modules.health.domain.models import RecordType
from src.modules.health.infrastructure.s3_provider import get_s3_provider
from src.modules.health_records.service import health_record_service
from src.modules.identity_access.models import Role

router = APIRouter(prefix="/health-records", tags=["health-records"])


def _paginate(items: list, page: int, page_size: int) -> tuple[list, int]:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total


class HealthRecordCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_user_id: str
    # Support both old format (data_type/summary) and new M05.1 format (record_type/data)
    record_type: RecordType | str | None = Field(default=None, description="Type of health record (M05.1)")
    data_type: str | None = Field(default=None, description="Type of health record (legacy)")
    data: dict | None = Field(default=None, description="Clinical data in JSONB format (M05.1)")
    summary: str | None = Field(default=None, description="Text summary (legacy)")
    object_key: str | None = None


class HealthRecordResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    patient_id: str
    created_by_id: str
    record_type: str
    data: dict
    created_at: datetime
    updated_at: datetime


def _enforce_consent(claims: dict, subject_user_id: str, required_scope: str) -> None:
    decision = consent_policy_evaluator.evaluate(
        actor_user_id=claims["sub"],
        actor_role=Role(claims["role"]),
        subject_user_id=subject_user_id,
        required_scope=required_scope,
        now=datetime.now(UTC),
    )
    if not decision:
        raise HTTPException(status_code=403, detail="Consent policy denied access")


@router.post("/")
def create_health_record(payload: HealthRecordCreateRequest, request: Request, claims: dict = Depends(_get_claims)):
    """Create a new health record with M05.1 domain layer.
    
    Supports both legacy format (data_type/summary) and M05.1 format (record_type/data).
    Requires health:write permission and consent from the record subject.
    """
    permissions = set(claims.get("permissions", []))
    if "health:write" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: health:write")

    _enforce_consent(claims=claims, subject_user_id=payload.subject_user_id, required_scope="health:write")
    
    # Support both legacy and M05.1 formats
    if payload.record_type is not None:
        # M05.1 format (new)
        rt_value = payload.record_type.value if isinstance(payload.record_type, RecordType) else str(payload.record_type)
        # Try to convert to enum, default to medical_history if not recognized
        try:
            rt = RecordType(rt_value)
        except ValueError:
            rt = RecordType.medical_history
        data = payload.data or {"summary": payload.summary or ""}
    elif payload.data_type is not None:
        # Legacy format - use data_type as-is
        rt_value = payload.data_type
        # Try to convert to enum, default to medical_history if not recognized
        try:
            rt = RecordType(rt_value)
        except ValueError:
            rt = RecordType.medical_history
        data = {"summary": payload.summary or ""}
    else:
        raise HTTPException(status_code=400, detail="Must provide either record_type or data_type")
    
    # Create via M05.1 application service
    record = health_record_service_m05.create(
        patient_id=payload.subject_user_id,
        created_by_id=claims["sub"],
        record_type=rt,
        data=data,
    )

    audit_log_store.append_event(
        actor_user_id=claims["sub"],
        action="phi.write",
        resource_type="health_record",
        resource_id=record.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        metadata={"subject_user_id": payload.subject_user_id, "record_type": record.record_type.value},
    )
    
    item = {
        "id": record.id,
        "patient_id": record.patient_id,
        "created_by_id": record.created_by_id,
        "record_type": record.record_type.value,
        "data": record.data,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    return success_response(data=item, message="health_record.created")


@router.get("/{record_id}")
def get_health_record(record_id: str, request: Request, claims: dict = Depends(_get_claims)):
    """Retrieve a specific health record by ID.
    
    Applies consent checks - user must have consent from the record subject.
    """
    permissions = set(claims.get("permissions", []))
    if "health:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: health:read")

    # Get via existing service (temporary until full migration)
    record = health_record_service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")

    _enforce_consent(claims=claims, subject_user_id=record.subject_user_id, required_scope="health:read")

    audit_log_store.append_event(
        actor_user_id=claims["sub"],
        action="phi.read",
        resource_type="health_record",
        resource_id=record.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        metadata={"subject_user_id": record.subject_user_id, "record_type": record.data_type},
    )
    return success_response(data=record.model_dump(), message="health_record.fetched")


@router.get("/")
def list_health_records(
    subject_user_id: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _consent: None = Depends(require_consent("health:read")),
    claims: dict = Depends(_get_claims),
):
    """List all health records for a patient (with consent check).
    
    Subject must have granted health:read consent to the requesting user.
    """
    permissions = set(claims.get("permissions", []))
    if "health:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: health:read")
    
    records = health_record_service.list_records(subject_user_id=subject_user_id)
    paged_records, total = _paginate(records, page=page, page_size=page_size)

    audit_log_store.append_event(
        actor_user_id=claims["sub"],
        action="phi.read_list",
        resource_type="health_record",
        resource_id=subject_user_id,
        correlation_id=getattr(request.state, "correlation_id", None),
        metadata={
            "subject_user_id": subject_user_id,
            "count": str(len(paged_records)),
            "total": str(total),
            "page": str(page),
            "page_size": str(page_size),
        },
    )
    return list_response(
        items=[r.model_dump() for r in paged_records],
        page=page,
        page_size=page_size,
        total=total,
        message="health_records.list",
    )


@router.get("/{record_id}/document-download-url")
def get_document_download_url(
    record_id: str,
    request: Request,
    claims: dict = Depends(_get_claims),
):
    permissions = set(claims.get("permissions", []))
    if "health:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: health:read")

    record = health_record_service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")

    _enforce_consent(claims=claims, subject_user_id=record.subject_user_id, required_scope="health:read")

    if not record.object_key:
        raise HTTPException(status_code=404, detail="No document attached to this health record")

    provider = get_s3_provider()
    download_url = provider.get_presigned_url(record.object_key, expiration_seconds=900)

    audit_log_store.append_event(
        actor_user_id=claims["sub"],
        action="phi.download_url",
        resource_type="health_record",
        resource_id=record.id,
        correlation_id=getattr(request.state, "correlation_id", None),
        metadata={
            "subject_user_id": record.subject_user_id,
            "object_key": record.object_key,
        },
    )
    item = {
        "record_id": record.id,
        "object_key": record.object_key,
        "download_url": download_url,
        "expires_in_seconds": 900,
    }
    return success_response(data=item, message="health_record.download_url")


@router.get("/search/by-type")
def search_health_records_by_type(
    subject_user_id: str,
    record_type: RecordType = Query(description="Filter by record type"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    request: Request = None,
    _consent: None = Depends(require_consent("health:read")),
    claims: dict = Depends(_get_claims),
):
    """Search health records by type with M05.1 domain layer.
    
    Applies RecordType enum validation and consent checks.
    """
    permissions = set(claims.get("permissions", []))
    if "health:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: health:read")

    records = health_record_service_m05.search(
        patient_id=subject_user_id,
        record_type=record_type,
    )
    paged_records, total = _paginate(records, page=page, page_size=page_size)

    audit_log_store.append_event(
        actor_user_id=claims["sub"],
        action="phi.read_search",
        resource_type="health_record",
        resource_id=subject_user_id,
        correlation_id=getattr(request.state, "correlation_id", None),
        metadata={
            "subject_user_id": subject_user_id,
            "record_type": record_type.value,
            "count": str(len(paged_records)),
            "total": str(total),
            "page": str(page),
            "page_size": str(page_size),
        },
    )
    
    return list_response(
        items=[
            {
                "id": r.id,
                "patient_id": r.patient_id,
                "created_by_id": r.created_by_id,
                "record_type": r.record_type.value,
                "data": r.data,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in paged_records
        ],
        page=page,
        page_size=page_size,
        total=total,
        message="health_records.search.by_type",
        filters={"record_type": record_type.value},
    )


@router.get("/search/by-date-range")
def search_health_records_by_date_range(
    subject_user_id: str,
    date_from: datetime = Query(description="Search from date (ISO 8601)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    request: Request = None,
    _consent: None = Depends(require_consent("health:read")),
    claims: dict = Depends(_get_claims),
):
    """Search health records by date range with M05.1 domain layer.
    
    Returns records created on or after date_from.
    """
    permissions = set(claims.get("permissions", []))
    if "health:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: health:read")

    records = health_record_service_m05.search(
        patient_id=subject_user_id,
        date_from=date_from,
    )
    paged_records, total = _paginate(records, page=page, page_size=page_size)

    audit_log_store.append_event(
        actor_user_id=claims["sub"],
        action="phi.read_search",
        resource_type="health_record",
        resource_id=subject_user_id,
        correlation_id=getattr(request.state, "correlation_id", None),
        metadata={
            "subject_user_id": subject_user_id,
            "date_from": date_from.isoformat(),
            "count": str(len(paged_records)),
            "total": str(total),
            "page": str(page),
            "page_size": str(page_size),
        },
    )
    
    return list_response(
        items=[
            {
                "id": r.id,
                "patient_id": r.patient_id,
                "created_by_id": r.created_by_id,
                "record_type": r.record_type.value,
                "data": r.data,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in paged_records
        ],
        page=page,
        page_size=page_size,
        total=total,
        message="health_records.search.by_date",
        filters={"date_from": date_from.isoformat()},
    )
