from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.interfaces.api.v1.auth import _get_claims
from src.metrics import metrics_recorder
from src.modules.caregiver_marketplace.service import caregiver_marketplace_service
from src.modules.subscriptions.service import subscription_service

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def _paginate(items: list, page: int, page_size: int) -> tuple[list, int]:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total


class MatchRequest(BaseModel):
    location: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_language: str | None = None


class VerificationReviewRequest(BaseModel):
    approve: bool
    notes: str | None = None


class OnboardingRequest(BaseModel):
    full_name: str
    skills: list[str] = Field(default_factory=list)
    location: str
    availability: str
    languages: list[str] = Field(default_factory=list)
    geography: str | None = None
    bio: str | None = None


class CredentialSubmissionRequest(BaseModel):
    credential_type: str
    document_ref: str | None = None
    issuer: str | None = None


class BookingRequest(BaseModel):
    caregiver_id: str
    start_time: str
    notes: str | None = None


class BookingReviewRequest(BaseModel):
    accept: bool


class RatingRequest(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = None


class IncidentReportRequest(BaseModel):
    severity: str
    description: str


class ModerationActionRequest(BaseModel):
    action: str


class ExtensionHooksRequest(BaseModel):
    pricing_strategy: str | None = None
    recommendation_strategy: str | None = None


@router.post("/caregivers/onboarding")
def upsert_onboarding(payload: OnboardingRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" not in permissions and "marketplace:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace permission")

    caregiver = caregiver_marketplace_service.onboarding_create_or_update(
        caregiver_user_id=claims["sub"],
        full_name=payload.full_name,
        skills=payload.skills,
        location=payload.location,
        availability=payload.availability,
        languages=payload.languages,
        geography=payload.geography,
        bio=payload.bio,
    )
    return caregiver.model_dump()


@router.get("/caregivers")
def list_caregivers(
    claims: dict = Depends(_get_claims),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    query: str | None = None,
    location: str | None = None,
    skill: str | None = None,
    language: str | None = None,
    availability: str | None = None,
    geography: str | None = None,
):
    permissions = set(claims.get("permissions", []))
    if "marketplace:read" not in permissions and "marketplace:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace access permission")

    caregivers = caregiver_marketplace_service.search(
        query=query,
        location=location,
        skill=skill,
        language=language,
        availability=availability,
        geography=geography,
    )
    paged_items, total = _paginate(caregivers, page=page, page_size=page_size)
    return {
        "count": len(paged_items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [c.model_dump() for c in paged_items],
    }


@router.post("/match")
def match_caregivers(payload: MatchRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:read" not in permissions and "marketplace:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace access permission")

    matches = caregiver_marketplace_service.match(
        location=payload.location,
        required_skills=payload.required_skills,
        preferred_language=payload.preferred_language,
    )
    return {"count": len(matches), "items": [m.model_dump() for m in matches]}


@router.post("/caregivers/{caregiver_id}/credentials")
def submit_credential(caregiver_id: str, payload: CredentialSubmissionRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" not in permissions and "marketplace:verify" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission for credential submit")
    try:
        credential = caregiver_marketplace_service.submit_credential(
            caregiver_id=caregiver_id,
            credential_type=payload.credential_type,
            document_ref=payload.document_ref,
            issuer=payload.issuer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return credential.model_dump()


@router.get("/caregivers/{caregiver_id}/credentials")
def list_credentials(
    caregiver_id: str,
    claims: dict = Depends(_get_claims),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    permissions = set(claims.get("permissions", []))
    if "marketplace:verify" not in permissions and "marketplace:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: marketplace:verify")
    records = caregiver_marketplace_service.list_credentials(caregiver_id)
    paged_items, total = _paginate(records, page=page, page_size=page_size)
    return {
        "count": len(paged_items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [record.model_dump() for record in paged_items],
    }


@router.post("/caregivers/{caregiver_id}/verification-submit")
def submit_verification(caregiver_id: str, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" not in permissions and "marketplace:verify" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission for verification submit")
    try:
        caregiver = caregiver_marketplace_service.submit_verification(caregiver_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return caregiver.model_dump()


@router.post("/caregivers/{caregiver_id}/verification-review")
def review_verification(caregiver_id: str, payload: VerificationReviewRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:verify" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: marketplace:verify")
    try:
        caregiver = caregiver_marketplace_service.review_verification(
            caregiver_id=caregiver_id,
            approve=payload.approve,
            reviewer_user_id=claims["sub"],
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return caregiver.model_dump()


@router.post("/bookings")
def create_booking(payload: BookingRequest, claims: dict = Depends(_get_claims)):
    if not subscription_service.has_entitlement(claims["sub"], "marketplace.booking"):
        raise HTTPException(status_code=403, detail="Entitlement required: marketplace.booking")

    try:
        booking = caregiver_marketplace_service.create_booking(
            caregiver_id=payload.caregiver_id,
            family_user_id=claims["sub"],
            start_time=payload.start_time,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    metrics_recorder.observe_marketplace_conversion("booking_requested")
    return booking.model_dump()


@router.post("/bookings/{booking_id}/review")
def review_booking(booking_id: str, payload: BookingReviewRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" not in permissions and "marketplace:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace permission")
    try:
        booking = caregiver_marketplace_service.review_booking(booking_id=booking_id, accept=payload.accept)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return booking.model_dump()


@router.post("/bookings/{booking_id}/complete")
def complete_booking(booking_id: str, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" not in permissions and "marketplace:read" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace permission")
    try:
        booking = caregiver_marketplace_service.complete_booking(booking_id=booking_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    metrics_recorder.observe_marketplace_conversion("booking_completed")
    return booking.model_dump()


@router.get("/bookings")
def list_bookings(
    claims: dict = Depends(_get_claims),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" in permissions:
        bookings = caregiver_marketplace_service.list_bookings()
    else:
        bookings = caregiver_marketplace_service.list_bookings(family_user_id=claims["sub"])
    paged_items, total = _paginate(bookings, page=page, page_size=page_size)
    return {
        "count": len(paged_items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [b.model_dump() for b in paged_items],
    }


@router.post("/caregivers/{caregiver_id}/ratings")
def rate_caregiver(caregiver_id: str, payload: RatingRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:read" not in permissions and "marketplace:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace permission")
    try:
        rating = caregiver_marketplace_service.rate_caregiver(
            caregiver_id=caregiver_id,
            family_user_id=claims["sub"],
            score=payload.score,
            comment=payload.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return rating.model_dump()


@router.get("/caregivers/{caregiver_id}/ratings")
def list_ratings(
    caregiver_id: str,
    claims: dict = Depends(_get_claims),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    permissions = set(claims.get("permissions", []))
    if "marketplace:read" not in permissions and "marketplace:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace permission")
    ratings = caregiver_marketplace_service.list_ratings(caregiver_id=caregiver_id)
    paged_items, total = _paginate(ratings, page=page, page_size=page_size)
    return {
        "count": len(paged_items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [r.model_dump() for r in paged_items],
    }


@router.post("/caregivers/{caregiver_id}/incidents")
def report_incident(caregiver_id: str, payload: IncidentReportRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:read" not in permissions and "marketplace:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace permission")
    try:
        report = caregiver_marketplace_service.report_incident(
            caregiver_id=caregiver_id,
            reported_by_user_id=claims["sub"],
            severity=payload.severity,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return report.model_dump()


@router.get("/incidents")
def list_incidents(
    claims: dict = Depends(_get_claims),
    caregiver_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" not in permissions and "marketplace:verify" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace moderation permission")
    items = caregiver_marketplace_service.list_incidents(caregiver_id=caregiver_id)
    paged_items, total = _paginate(items, page=page, page_size=page_size)
    return {
        "count": len(paged_items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [i.model_dump() for i in paged_items],
    }


@router.post("/incidents/{report_id}/moderate")
def moderate_incident(report_id: str, payload: ModerationActionRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" not in permissions and "marketplace:verify" not in permissions:
        raise HTTPException(status_code=403, detail="Missing marketplace moderation permission")
    try:
        report = caregiver_marketplace_service.moderate_incident(report_id=report_id, action=payload.action)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return report.model_dump()


@router.get("/extensions")
def get_extensions(claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: marketplace:manage")
    return caregiver_marketplace_service.get_extension_hooks().model_dump()


@router.post("/extensions")
def set_extensions(payload: ExtensionHooksRequest, claims: dict = Depends(_get_claims)):
    permissions = set(claims.get("permissions", []))
    if "marketplace:manage" not in permissions:
        raise HTTPException(status_code=403, detail="Missing permission: marketplace:manage")
    hooks = caregiver_marketplace_service.set_extension_hooks(
        pricing_strategy=payload.pricing_strategy,
        recommendation_strategy=payload.recommendation_strategy,
    )
    return hooks.model_dump()
