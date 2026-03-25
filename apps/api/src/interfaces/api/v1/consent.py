from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.api.v1.auth import _get_claims
from src.modules.audit_logging.store import audit_log_store
from src.modules.consent_access.service import consent_service
from src.modules.identity_access.models import Role

router = APIRouter(prefix="/consent", tags=["consent"])


class GrantConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accessor_user_id: str
    scopes: list[str] = Field(min_length=1)
    subject_user_id: str | None = None
    expires_in_days: int = Field(default=30, ge=1, le=365)


class RequestConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_user_id: str
    accessor_user_id: str
    scopes: list[str] = Field(min_length=1)
    reason: str | None = None
    expires_in_days: int = Field(default=30, ge=1, le=365)


class ReviewConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approve: bool
    review_notes: str | None = None


class RenewConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extend_days: int = Field(default=30, ge=1, le=365)
    reason: str | None = None


class BreakGlassRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_user_id: str
    scopes: list[str] = Field(min_length=1)
    reason: str = Field(min_length=8)
    duration_minutes: int = Field(default=60, ge=1, le=240)


class DisputeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_user_id: str
    accessor_user_id: str
    reason: str = Field(min_length=5)
    grant_id: str | None = None


class DisputeResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_notes: str = Field(min_length=5)


class RevokeGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


@router.get("/scopes")
def list_scopes(claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "consent:manage" not in permissions and "identity:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing consent visibility permission")

    scopes = consent_service.allowed_scopes()
    return {"count": len(scopes), "items": scopes}


@router.post("/requests")
def create_consent_request(payload: RequestConsentRequest, claims: dict = Depends(_get_claims)):
    actor_role = Role(claims["role"])
    actor_id = claims["sub"]
    if actor_role != Role.admin and payload.subject_user_id != actor_id and payload.accessor_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only admin or involved parties can create request")

    try:
        request_record = consent_service.request_consent(
            subject_user_id=payload.subject_user_id,
            accessor_user_id=payload.accessor_user_id,
            scopes=payload.scopes,
            requested_by_user_id=actor_id,
            request_reason=payload.reason,
            expires_in_days=payload.expires_in_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return request_record.model_dump()


@router.post("/requests/{grant_id}/review")
def review_consent_request(grant_id: str, payload: ReviewConsentRequest, claims: dict = Depends(_get_claims)):
    actor_role = Role(claims["role"])
    actor_id = claims["sub"]
    grant = consent_service.grants.get(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    if actor_role != Role.admin and grant.subject_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only subject or admin can review request")

    reviewed = consent_service.review_consent_request(
        grant_id=grant_id,
        approve=payload.approve,
        reviewed_by_user_id=actor_id,
        review_notes=payload.review_notes,
    )
    if not reviewed:
        raise HTTPException(status_code=404, detail="Grant not found")
    return reviewed.model_dump()


@router.post("/grants")
def create_grant(payload: GrantConsentRequest, claims: dict = Depends(_get_claims)):
    actor_role = Role(claims["role"])
    actor_id = claims["sub"]
    subject_user_id = payload.subject_user_id or actor_id

    if actor_role != Role.admin and subject_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only admin can grant consent for another user")

    try:
        grant = consent_service.grant_consent(
            subject_user_id=subject_user_id,
            accessor_user_id=payload.accessor_user_id,
            scopes=payload.scopes,
            expires_in_days=payload.expires_in_days,
            actor_user_id=actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return grant.model_dump()


@router.post("/grant")
def create_grant_alias(payload: GrantConsentRequest, claims: dict = Depends(_get_claims)):
    return create_grant(payload=payload, claims=claims)


@router.delete("/grants/{grant_id}")
def revoke_grant(grant_id: str, reason: str | None = None, claims: dict = Depends(_get_claims)):
    grant = consent_service.grants.get(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    actor_role = Role(claims["role"])
    actor_id = claims["sub"]
    if actor_role != Role.admin and grant.subject_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only subject or admin can revoke consent")

    revoked = consent_service.revoke_consent(grant_id=grant_id, actor_user_id=actor_id, revoke_reason=reason)
    if not revoked:
        raise HTTPException(status_code=404, detail="Grant not found")
    return revoked.model_dump()


@router.post("/grant/{grant_id}/revoke")
def revoke_grant_alias(grant_id: str, payload: RevokeGrantRequest, claims: dict = Depends(_get_claims)):
    return revoke_grant(grant_id=grant_id, reason=payload.reason, claims=claims)


@router.post("/grants/{grant_id}/renew")
def renew_grant(grant_id: str, payload: RenewConsentRequest, claims: dict = Depends(_get_claims)):
    grant = consent_service.grants.get(grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    actor_role = Role(claims["role"])
    actor_id = claims["sub"]
    if actor_role != Role.admin and grant.subject_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only subject or admin can renew consent")

    renewed = consent_service.renew_consent(
        grant_id=grant_id,
        extend_days=payload.extend_days,
        actor_user_id=actor_id,
        reason=payload.reason,
    )
    if not renewed:
        raise HTTPException(status_code=400, detail="Grant cannot be renewed in current state")
    return renewed.model_dump()


@router.get("/grants")
def list_grants(subject_user_id: str | None = None, claims: dict = Depends(_get_claims)):
    actor_role = Role(claims["role"])
    actor_id = claims["sub"]
    if actor_role != Role.admin:
        subject_user_id = actor_id

    grants = consent_service.list_grants(subject_user_id=subject_user_id)
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "count": len(grants),
        "items": [g.model_dump() for g in grants],
    }


@router.get("/grants/mine")
def list_my_grants(claims: dict = Depends(_get_claims)):
    grants = consent_service.list_grants(subject_user_id=claims["sub"])
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "count": len(grants),
        "items": [g.model_dump() for g in grants],
    }


@router.get("/check-access")
def check_access(subject_user_id: str, scope: str, claims: dict = Depends(_get_claims)):
    allowed = consent_service.granted_scopes_for(
        subject_user_id=subject_user_id,
        accessor_user_id=claims["sub"],
        now=datetime.now(UTC),
    )
    break_glass = consent_service.active_break_glass_scopes_for(
        actor_user_id=claims["sub"],
        subject_user_id=subject_user_id,
        now=datetime.now(UTC),
    )
    all_scopes = allowed.union(break_glass)
    domain_wildcard = f"{scope.split(':', 1)[0]}:*" if ":" in scope else None
    is_allowed = (
        claims["sub"] == subject_user_id
        or Role(claims["role"]) == Role.admin
        or scope in all_scopes
        or "*:*" in all_scopes
        or (domain_wildcard in all_scopes if domain_wildcard else False)
    )
    return {"allowed": is_allowed, "subject_user_id": subject_user_id, "scope": scope}


@router.post("/break-glass")
def break_glass(payload: BreakGlassRequest, claims: dict = Depends(_get_claims)):
    actor_id = claims["sub"]
    actor_role = Role(claims["role"])
    if actor_role not in {Role.admin, Role.doctor}:
        raise HTTPException(status_code=403, detail="Only admin and doctor can activate break-glass")

    try:
        record = consent_service.activate_break_glass(
            actor_user_id=actor_id,
            subject_user_id=payload.subject_user_id,
            scopes=payload.scopes,
            reason=payload.reason,
            approved_by_user_id=actor_id if actor_role == Role.admin else None,
            duration_minutes=payload.duration_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit_log_store.append_event(
        actor_user_id=actor_id,
        action="consent.break_glass",
        resource_type="consent",
        resource_id=record.id,
        metadata={
            "subject_user_id": payload.subject_user_id,
            "reason": payload.reason,
            "duration_minutes": str(payload.duration_minutes),
        },
    )
    return record.model_dump()


@router.get("/evidence")
def list_evidence(
    subject_user_id: str | None = None,
    accessor_user_id: str | None = None,
    event_type: str | None = None,
    since: datetime | None = None,
    claims: dict = Depends(_get_claims),
):
    actor_role = Role(claims["role"])
    actor_id = claims["sub"]
    if actor_role != Role.admin:
        subject_user_id = subject_user_id or actor_id
        if subject_user_id != actor_id and accessor_user_id != actor_id:
            raise HTTPException(status_code=403, detail="Cannot inspect other users' consent evidence")

    records = consent_service.list_evidence(
        subject_user_id=subject_user_id,
        accessor_user_id=accessor_user_id,
        event_type=event_type,
        since=since,
    )
    return {"count": len(records), "items": [record.model_dump() for record in records]}


@router.post("/disputes")
def create_dispute(payload: DisputeCreateRequest, claims: dict = Depends(_get_claims)):
    actor_id = claims["sub"]
    actor_role = Role(claims["role"])
    if actor_role != Role.admin and actor_id not in {payload.subject_user_id, payload.accessor_user_id}:
        raise HTTPException(status_code=403, detail="Only involved parties can open dispute")

    dispute = consent_service.create_dispute(
        created_by_user_id=actor_id,
        subject_user_id=payload.subject_user_id,
        accessor_user_id=payload.accessor_user_id,
        reason=payload.reason,
        grant_id=payload.grant_id,
    )
    return dispute.model_dump()


@router.get("/disputes")
def list_disputes(open_only: bool = False, claims: dict = Depends(_get_claims)):
    actor_role = Role(claims["role"])
    actor_id = claims["sub"]
    items = consent_service.list_disputes(only_open=open_only)
    if actor_role == Role.admin:
        return {"count": len(items), "items": [item.model_dump() for item in items]}

    visible = [
        item
        for item in items
        if item.subject_user_id == actor_id or item.accessor_user_id == actor_id or item.created_by_user_id == actor_id
    ]
    return {"count": len(visible), "items": [item.model_dump() for item in visible]}


@router.post("/disputes/{dispute_id}/resolve")
def resolve_dispute(dispute_id: str, payload: DisputeResolveRequest, claims: dict = Depends(_get_claims)):
    actor_role = Role(claims["role"])
    if actor_role != Role.admin:
        raise HTTPException(status_code=403, detail="Only admin can resolve consent disputes")

    resolved = consent_service.resolve_dispute(
        dispute_id=dispute_id,
        resolved_by_user_id=claims["sub"],
        resolution_notes=payload.resolution_notes,
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return resolved.model_dump()
