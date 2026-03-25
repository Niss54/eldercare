from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.api.v1.auth import _get_claims
from src.modules.audit_logging.store import AuditCategory, AuditOutcome, AuditSeverity, audit_log_store

router = APIRouter(prefix="/audit", tags=["audit"])


def _paginate(items: list, page: int, page_size: int) -> tuple[list, int]:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total


class RetentionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    days_to_keep: int = Field(default=90, ge=1, le=3650)


class ArchiveOldRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keep_last: int = Field(default=500, ge=1, le=100000)
    reason: str = Field(default="retention_policy")


def _require_audit_permission(claims: dict) -> None:
    permissions = set(claims.get("permissions", []))
    if "audit:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: audit:read")


@router.get("/events")
def list_audit_events(
    claims: dict = Depends(_get_claims),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    user_id: str | None = None,
    actor_user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    correlation_id: str | None = None,
    category: AuditCategory | None = None,
    severity: AuditSeverity | None = None,
    outcome: AuditOutcome | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
):
    _require_audit_permission(claims)
    target_actor = user_id or actor_user_id

    events = audit_log_store.list_events(
        actor_user_id=target_actor,
        action=action,
        resource_type=resource_type,
        correlation_id=correlation_id,
        category=category,
        severity=severity,
        outcome=outcome,
        since=since,
        until=until,
    )
    paged_events, total = _paginate(events, page=page, page_size=page_size)
    return {
        "count": len(paged_events),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [event.model_dump() for event in paged_events],
    }


@router.get("/incidents")
def list_audit_incidents(
    claims: dict = Depends(_get_claims),
    severity: AuditSeverity | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    _require_audit_permission(claims)
    items = audit_log_store.list_anomalies(severity=severity)
    paged_items, total = _paginate(items, page=page, page_size=page_size)
    return {
        "count": len(paged_items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item.model_dump() for item in paged_items],
    }


@router.get("/compliance/report")
def compliance_report(claims: dict = Depends(_get_claims), since: datetime | None = None, until: datetime | None = None):
    _require_audit_permission(claims)
    return audit_log_store.compliance_report(since=since, until=until)


@router.get("/checkpoints")
def list_checkpoints(claims: dict = Depends(_get_claims)):
    _require_audit_permission(claims)
    checkpoints = audit_log_store.checkpoints
    return {
        "count": len(checkpoints),
        "total": len(checkpoints),
        "page": 1,
        "page_size": len(checkpoints) if checkpoints else 0,
        "items": [item.model_dump() for item in checkpoints],
    }


@router.get("/archive")
def list_archive_batches(
    claims: dict = Depends(_get_claims),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    _require_audit_permission(claims)
    items = audit_log_store.list_archives()
    paged_items, total = _paginate(items, page=page, page_size=page_size)
    return {
        "count": len(paged_items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item.model_dump() for item in paged_items],
    }


@router.post("/archive")
def archive_old(claims: dict = Depends(_get_claims), payload: ArchiveOldRequest | None = None):
    _require_audit_permission(claims)
    payload = payload or ArchiveOldRequest()
    batch = audit_log_store.archive_old_events(keep_last=payload.keep_last, reason=payload.reason)
    if not batch:
        return {"status": "noop", "detail": "No events archived"}
    return {"status": "archived", "batch": batch.model_dump()}


@router.post("/retention/apply")
def apply_retention(payload: RetentionRequest, claims: dict = Depends(_get_claims)):
    _require_audit_permission(claims)
    batch = audit_log_store.apply_retention_policy(days_to_keep=payload.days_to_keep)
    if not batch:
        return {"status": "noop", "detail": "No events matched retention cutoff"}
    return {"status": "archived", "batch": batch.model_dump()}


@router.get("/verify-integrity")
def verify_audit_integrity(claims: dict = Depends(_get_claims)):
    _require_audit_permission(claims)

    valid, detail = audit_log_store.verify_chain()
    return {"valid": valid, "detail": detail}
