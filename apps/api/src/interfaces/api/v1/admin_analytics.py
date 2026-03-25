from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.api.v1.auth import _get_claims
from src.modules.admin_analytics.service import DashboardFilters, admin_analytics_service

router = APIRouter(prefix="/admin-analytics", tags=["admin-analytics"])


class DisableAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    reason: str = Field(min_length=3)


class ResendInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str | None = None


class IncidentReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    decision: str
    notes: str | None = None


class FeatureFlagUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    rollout_percentage: int = Field(default=100, ge=0, le=100)
    roles: list[str] = Field(default_factory=list)
    plans: list[str] = Field(default_factory=list)


def _require_admin(claims: dict) -> None:
    permissions = set(claims.get("permissions", []))
    if "analytics:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: analytics:read")
    if claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")


@router.get("/dashboard")
def dashboard(
    claims: dict = Depends(_get_claims),
    geography: str | None = None,
    role: str | None = None,
    plan: str | None = None,
    time_window: str | None = None,
):
    _require_admin(claims)
    return admin_analytics_service.dashboard(
        filters=DashboardFilters(
            geography=geography,
            role=role,
            plan=plan,
            time_window=time_window,
        )
    )


@router.get("/metrics/catalog")
def metric_catalog(claims: dict = Depends(_get_claims)):
    _require_admin(claims)
    return admin_analytics_service.metrics_catalog()


@router.post("/actions/disable-account")
def disable_account(payload: DisableAccountRequest, claims: dict = Depends(_get_claims)):
    _require_admin(claims)
    result = admin_analytics_service.disable_account(
        actor_user_id=claims["sub"],
        user_id=payload.user_id,
        reason=payload.reason,
    )
    return result.model_dump()


@router.post("/actions/resend-invite")
def resend_invite(payload: ResendInviteRequest, claims: dict = Depends(_get_claims)):
    _require_admin(claims)
    result = admin_analytics_service.resend_invite(
        actor_user_id=claims["sub"],
        request_id=payload.request_id,
    )
    return result.model_dump()


@router.post("/actions/incident-review")
def incident_review(payload: IncidentReviewRequest, claims: dict = Depends(_get_claims)):
    _require_admin(claims)
    result = admin_analytics_service.review_incident(
        actor_user_id=claims["sub"],
        incident_id=payload.incident_id,
        decision=payload.decision,
        notes=payload.notes,
    )
    return result.model_dump()


@router.get("/reports/export")
def export_report(
    claims: dict = Depends(_get_claims),
    format: str = "json",
    geography: str | None = None,
    role: str | None = None,
    plan: str | None = None,
    time_window: str | None = None,
):
    _require_admin(claims)
    filters = DashboardFilters(
        geography=geography,
        role=role,
        plan=plan,
        time_window=time_window,
    )
    try:
        content_type, body = admin_analytics_service.export_dashboard(format, filters)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = f"admin-report-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.{ 'csv' if format == 'csv' else 'json' }"
    return Response(
        content=body,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/feature-flags")
def list_feature_flags(claims: dict = Depends(_get_claims)):
    _require_admin(claims)
    flags = admin_analytics_service.list_feature_flags()
    return {"count": len(flags), "items": [flag.model_dump() for flag in flags]}


@router.post("/feature-flags/{flag_key}")
def update_feature_flag(flag_key: str, payload: FeatureFlagUpdateRequest, claims: dict = Depends(_get_claims)):
    _require_admin(claims)
    flag = admin_analytics_service.set_feature_flag(
        actor_user_id=claims["sub"],
        flag_key=flag_key,
        enabled=payload.enabled,
        rollout_percentage=payload.rollout_percentage,
        roles=payload.roles,
        plans=payload.plans,
    )
    return flag.model_dump()
