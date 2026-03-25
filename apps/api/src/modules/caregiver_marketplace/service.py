import secrets
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class CaregiverProfile(BaseModel):
    id: str
    user_id: str
    full_name: str
    bio: str | None = None
    skills: list[str]
    location: str
    languages: list[str] = Field(default_factory=list)
    geography: str | None = None
    availability: str
    rating: float
    ratings_count: int = 0
    trust_score: float = 0.0
    verification_status: VerificationStatus
    moderation_status: str = "active"
    recommendation_tags: list[str] = Field(default_factory=list)
    dynamic_pricing_enabled: bool = False
    created_at: datetime
    updated_at: datetime


class CredentialRecord(BaseModel):
    id: str
    caregiver_id: str
    credential_type: str
    document_ref: str | None = None
    issuer: str | None = None
    status: VerificationStatus
    review_notes: str | None = None
    reviewed_by: str | None = None
    created_at: datetime
    updated_at: datetime


class BookingStatus(str, Enum):
    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"
    confirmed = "confirmed"
    completed = "completed"


class Booking(BaseModel):
    id: str
    caregiver_id: str
    family_user_id: str
    start_time: str
    notes: str | None = None
    status: BookingStatus
    reviewed_by_caregiver: bool = False
    created_at: datetime
    updated_at: datetime


class MatchResult(BaseModel):
    caregiver: CaregiverProfile
    score: float
    rationale: dict[str, str]


class CaregiverRating(BaseModel):
    id: str
    caregiver_id: str
    family_user_id: str
    score: int
    comment: str | None = None
    created_at: datetime


class IncidentReport(BaseModel):
    id: str
    caregiver_id: str
    reported_by_user_id: str
    severity: str
    description: str
    status: str = "open"
    moderation_action: str | None = None
    created_at: datetime
    updated_at: datetime


class MarketplaceExtensionHooks(BaseModel):
    pricing_strategy: str = "flat"
    recommendation_strategy: str = "rule_v1"


class CaregiverMarketplaceService:
    def __init__(self):
        self.caregivers: dict[str, CaregiverProfile] = {}
        self.credentials: dict[str, CredentialRecord] = {}
        self.bookings: dict[str, Booking] = {}
        self.ratings: dict[str, CaregiverRating] = {}
        self.incident_reports: dict[str, IncidentReport] = {}
        self.search_index: dict[str, set[str]] = {}
        self.extension_hooks = MarketplaceExtensionHooks()

    def seed_if_empty(self) -> None:
        if self.caregivers:
            return
        base = [
            {
                "user_id": "u_caregiver",
                "full_name": "Anika Rao",
                "bio": "Certified caregiver with medication and mobility expertise.",
                "skills": ["mobility", "medication", "companionship"],
                "location": "Bangalore",
                "languages": ["en", "hi"],
                "geography": "bangalore-east",
                "availability": "weekday-mornings",
                "rating": 4.8,
                "ratings_count": 12,
                "trust_score": 0.93,
                "verification_status": VerificationStatus.approved,
                "recommendation_tags": ["medication", "mobility"],
            },
            {
                "user_id": "u_caregiver_2",
                "full_name": "Neha Mehta",
                "bio": "Post-op and nutrition support specialist.",
                "skills": ["post-op", "nutrition"],
                "location": "Bangalore",
                "languages": ["en", "kn"],
                "geography": "bangalore-west",
                "availability": "weekday-evenings",
                "rating": 4.5,
                "ratings_count": 8,
                "trust_score": 0.86,
                "verification_status": VerificationStatus.pending,
                "recommendation_tags": ["post-op"],
            },
        ]
        for item in base:
            now = datetime.now(UTC)
            caregiver = CaregiverProfile(
                id=secrets.token_urlsafe(10),
                created_at=now,
                updated_at=now,
                **item,
            )
            self.caregivers[caregiver.id] = caregiver
        self._rebuild_search_index()

    def _rebuild_search_index(self) -> None:
        index: dict[str, set[str]] = {}
        for caregiver in self.caregivers.values():
            tokens = set()
            tokens.update(caregiver.full_name.lower().split())
            tokens.update(skill.lower() for skill in caregiver.skills)
            tokens.update(language.lower() for language in caregiver.languages)
            tokens.add(caregiver.location.lower())
            if caregiver.geography:
                tokens.add(caregiver.geography.lower())
            for token in tokens:
                index.setdefault(token, set()).add(caregiver.id)
        self.search_index = index

    def onboarding_create_or_update(
        self,
        caregiver_user_id: str,
        full_name: str,
        skills: list[str],
        location: str,
        availability: str,
        languages: list[str],
        geography: str | None,
        bio: str | None,
    ) -> CaregiverProfile:
        now = datetime.now(UTC)
        existing = next((c for c in self.caregivers.values() if c.user_id == caregiver_user_id), None)
        if existing:
            existing.full_name = full_name
            existing.skills = sorted(set(skills))
            existing.location = location
            existing.availability = availability
            existing.languages = sorted(set(languages))
            existing.geography = geography
            existing.bio = bio
            existing.updated_at = now
            self._rebuild_search_index()
            return existing

        profile = CaregiverProfile(
            id=secrets.token_urlsafe(10),
            user_id=caregiver_user_id,
            full_name=full_name,
            bio=bio,
            skills=sorted(set(skills)),
            location=location,
            languages=sorted(set(languages)),
            geography=geography,
            availability=availability,
            rating=0.0,
            ratings_count=0,
            trust_score=0.5,
            verification_status=VerificationStatus.draft,
            created_at=now,
            updated_at=now,
        )
        self.caregivers[profile.id] = profile
        self._rebuild_search_index()
        return profile

    def list_caregivers(self) -> list[CaregiverProfile]:
        self.seed_if_empty()
        return sorted(self.caregivers.values(), key=lambda c: (c.verification_status.value, -c.rating, -c.trust_score))

    def search(
        self,
        query: str | None = None,
        location: str | None = None,
        skill: str | None = None,
        language: str | None = None,
        availability: str | None = None,
        geography: str | None = None,
    ) -> list[CaregiverProfile]:
        candidates = self.list_caregivers()
        if query:
            q = query.lower().strip()
            direct_matches = self.search_index.get(q)
            if direct_matches:
                candidates = [c for c in candidates if c.id in direct_matches]
            else:
                candidates = [c for c in candidates if q in c.full_name.lower()]
        if location:
            candidates = [c for c in candidates if c.location.lower() == location.lower()]
        if geography:
            candidates = [c for c in candidates if (c.geography or "").lower() == geography.lower()]
        if skill:
            candidates = [c for c in candidates if skill.lower() in [s.lower() for s in c.skills]]
        if language:
            candidates = [c for c in candidates if language.lower() in [l.lower() for l in c.languages]]
        if availability:
            candidates = [c for c in candidates if availability.lower() in c.availability.lower()]
        return candidates

    def match(self, location: str, required_skills: list[str], preferred_language: str | None = None) -> list[MatchResult]:
        candidates = [c for c in self.list_caregivers() if c.location.lower() == location.lower() and c.moderation_status == "active"]
        required = {s.lower() for s in required_skills}

        def score(caregiver: CaregiverProfile) -> tuple[float, float, float]:
            skills = {s.lower() for s in caregiver.skills}
            overlap = len(required.intersection(skills))
            language_bonus = 0.5 if preferred_language and preferred_language.lower() in [l.lower() for l in caregiver.languages] else 0.0
            verification_bonus = 0.5 if caregiver.verification_status == VerificationStatus.approved else 0.0
            final_score = float(overlap) + caregiver.rating + caregiver.trust_score + language_bonus + verification_bonus
            return final_score, caregiver.rating, caregiver.trust_score

        ranked = sorted(candidates, key=score, reverse=True)
        results: list[MatchResult] = []
        for caregiver in ranked:
            skills = {s.lower() for s in caregiver.skills}
            overlap = len(required.intersection(skills))
            final_score, _, _ = score(caregiver)
            rationale = {
                "skill_overlap": str(overlap),
                "rating": f"{caregiver.rating:.2f}",
                "trust_score": f"{caregiver.trust_score:.2f}",
                "strategy": self.extension_hooks.recommendation_strategy,
            }
            results.append(MatchResult(caregiver=caregiver, score=round(final_score, 3), rationale=rationale))
        return results

    def submit_credential(
        self,
        caregiver_id: str,
        credential_type: str,
        document_ref: str | None,
        issuer: str | None,
    ) -> CredentialRecord:
        caregiver = self.caregivers.get(caregiver_id)
        if not caregiver:
            raise ValueError("caregiver not found")

        now = datetime.now(UTC)
        credential = CredentialRecord(
            id=secrets.token_urlsafe(10),
            caregiver_id=caregiver_id,
            credential_type=credential_type,
            document_ref=document_ref,
            issuer=issuer,
            status=VerificationStatus.submitted,
            created_at=now,
            updated_at=now,
        )
        self.credentials[credential.id] = credential
        caregiver.verification_status = VerificationStatus.pending
        caregiver.updated_at = now
        return credential

    def submit_verification(self, caregiver_id: str) -> CaregiverProfile:
        caregiver = self.caregivers.get(caregiver_id)
        if not caregiver:
            raise ValueError("caregiver not found")
        caregiver.verification_status = VerificationStatus.pending
        caregiver.updated_at = datetime.now(UTC)
        return caregiver

    def review_verification(self, caregiver_id: str, approve: bool, reviewer_user_id: str | None = None, notes: str | None = None) -> CaregiverProfile:
        caregiver = self.caregivers.get(caregiver_id)
        if not caregiver:
            raise ValueError("caregiver not found")
        caregiver.verification_status = VerificationStatus.approved if approve else VerificationStatus.rejected
        caregiver.updated_at = datetime.now(UTC)

        for credential in self.credentials.values():
            if credential.caregiver_id != caregiver_id:
                continue
            credential.status = caregiver.verification_status
            credential.review_notes = notes
            credential.reviewed_by = reviewer_user_id
            credential.updated_at = caregiver.updated_at
        return caregiver

    def list_credentials(self, caregiver_id: str) -> list[CredentialRecord]:
        return sorted(
            [c for c in self.credentials.values() if c.caregiver_id == caregiver_id],
            key=lambda item: item.created_at,
            reverse=True,
        )

    def create_booking(self, caregiver_id: str, family_user_id: str, start_time: str, notes: str | None) -> Booking:
        caregiver = self.caregivers.get(caregiver_id)
        if not caregiver:
            raise ValueError("caregiver not found")
        if caregiver.verification_status != VerificationStatus.approved:
            raise ValueError("caregiver is not approved")
        booking = Booking(
            id=secrets.token_urlsafe(10),
            caregiver_id=caregiver_id,
            family_user_id=family_user_id,
            start_time=start_time,
            notes=notes,
            status=BookingStatus.requested,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.bookings[booking.id] = booking
        return booking

    def review_booking(self, booking_id: str, accept: bool) -> Booking:
        booking = self.bookings.get(booking_id)
        if not booking:
            raise ValueError("booking not found")
        booking.reviewed_by_caregiver = True
        booking.status = BookingStatus.accepted if accept else BookingStatus.rejected
        booking.updated_at = datetime.now(UTC)
        return booking

    def complete_booking(self, booking_id: str) -> Booking:
        booking = self.bookings.get(booking_id)
        if not booking:
            raise ValueError("booking not found")
        booking.status = BookingStatus.completed
        booking.updated_at = datetime.now(UTC)
        return booking

    def rate_caregiver(self, caregiver_id: str, family_user_id: str, score: int, comment: str | None) -> CaregiverRating:
        caregiver = self.caregivers.get(caregiver_id)
        if not caregiver:
            raise ValueError("caregiver not found")
        if score < 1 or score > 5:
            raise ValueError("score must be between 1 and 5")
        rating = CaregiverRating(
            id=secrets.token_urlsafe(10),
            caregiver_id=caregiver_id,
            family_user_id=family_user_id,
            score=score,
            comment=comment,
            created_at=datetime.now(UTC),
        )
        self.ratings[rating.id] = rating

        caregiver_ratings = [r.score for r in self.ratings.values() if r.caregiver_id == caregiver_id]
        caregiver.ratings_count = len(caregiver_ratings)
        caregiver.rating = round(sum(caregiver_ratings) / len(caregiver_ratings), 2)
        caregiver.trust_score = round(min(1.0, 0.5 + (caregiver.rating / 10.0) + (caregiver.ratings_count / 100.0)), 3)
        caregiver.updated_at = datetime.now(UTC)
        return rating

    def list_ratings(self, caregiver_id: str) -> list[CaregiverRating]:
        return sorted(
            [r for r in self.ratings.values() if r.caregiver_id == caregiver_id],
            key=lambda item: item.created_at,
            reverse=True,
        )

    def report_incident(self, caregiver_id: str, reported_by_user_id: str, severity: str, description: str) -> IncidentReport:
        caregiver = self.caregivers.get(caregiver_id)
        if not caregiver:
            raise ValueError("caregiver not found")
        now = datetime.now(UTC)
        report = IncidentReport(
            id=secrets.token_urlsafe(10),
            caregiver_id=caregiver_id,
            reported_by_user_id=reported_by_user_id,
            severity=severity,
            description=description,
            created_at=now,
            updated_at=now,
        )
        self.incident_reports[report.id] = report
        return report

    def moderate_incident(self, report_id: str, action: str) -> IncidentReport:
        report = self.incident_reports.get(report_id)
        if not report:
            raise ValueError("incident report not found")
        report.status = "reviewed"
        report.moderation_action = action
        report.updated_at = datetime.now(UTC)

        caregiver = self.caregivers.get(report.caregiver_id)
        if caregiver:
            if action == "suspend":
                caregiver.moderation_status = "suspended"
            elif action == "warn":
                caregiver.moderation_status = "watchlist"
            elif action == "clear":
                caregiver.moderation_status = "active"
            caregiver.updated_at = report.updated_at
        return report

    def list_incidents(self, caregiver_id: str | None = None) -> list[IncidentReport]:
        reports = list(self.incident_reports.values())
        if caregiver_id:
            reports = [r for r in reports if r.caregiver_id == caregiver_id]
        return sorted(reports, key=lambda item: item.created_at, reverse=True)

    def set_extension_hooks(self, pricing_strategy: str | None = None, recommendation_strategy: str | None = None) -> MarketplaceExtensionHooks:
        if pricing_strategy:
            self.extension_hooks.pricing_strategy = pricing_strategy
        if recommendation_strategy:
            self.extension_hooks.recommendation_strategy = recommendation_strategy
        return self.extension_hooks

    def get_extension_hooks(self) -> MarketplaceExtensionHooks:
        return self.extension_hooks

    def list_bookings(self, family_user_id: str | None = None) -> list[Booking]:
        bookings = list(self.bookings.values())
        if family_user_id:
            bookings = [b for b in bookings if b.family_user_id == family_user_id]
        return sorted(bookings, key=lambda b: b.created_at, reverse=True)


caregiver_marketplace_service = CaregiverMarketplaceService()
