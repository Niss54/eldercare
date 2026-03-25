import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field


class GrantStatus(str, Enum):
    requested = "requested"
    granted = "granted"
    revoked = "revoked"
    expired = "expired"


class ConsentGrantRecord(BaseModel):
    id: str
    subject_user_id: str
    accessor_user_id: str
    scopes: list[str]
    status: GrantStatus = GrantStatus.granted
    request_reason: str | None = None
    review_notes: str | None = None
    reviewed_by_user_id: str | None = None
    requested_at: datetime
    granted_at: datetime | None = None
    created_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revoke_reason: str | None = None
    revoked: bool = False


class BreakGlassAccessRecord(BaseModel):
    id: str
    actor_user_id: str
    subject_user_id: str
    scopes: list[str]
    reason: str
    approved_by_user_id: str | None = None
    started_at: datetime
    expires_at: datetime


class ConsentEvidenceRecord(BaseModel):
    id: str
    grant_id: str | None = None
    subject_user_id: str
    accessor_user_id: str
    actor_user_id: str
    event_type: str
    reason: str | None = None
    timestamp: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class ConsentDisputeRecord(BaseModel):
    id: str
    grant_id: str | None = None
    created_by_user_id: str
    subject_user_id: str
    accessor_user_id: str
    reason: str
    status: str = "open"
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by_user_id: str | None = None
    resolution_notes: str | None = None


class ConsentService:
    def __init__(self):
        self.grants: dict[str, ConsentGrantRecord] = {}
        self.break_glass_events: dict[str, BreakGlassAccessRecord] = {}
        self.evidence_records: dict[str, ConsentEvidenceRecord] = {}
        self.disputes: dict[str, ConsentDisputeRecord] = {}
        self.scope_catalog: dict[str, set[str]] = {
            "health": {"read", "write", "share"},
            "medication": {"read", "manage"},
            "sos": {"trigger", "respond"},
            "notification": {"read", "send"},
            "marketplace": {"read", "manage", "verify"},
        }

    def _record_evidence(
        self,
        grant_id: str | None,
        subject_user_id: str,
        accessor_user_id: str,
        actor_user_id: str,
        event_type: str,
        reason: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ConsentEvidenceRecord:
        evidence = ConsentEvidenceRecord(
            id=secrets.token_urlsafe(10),
            grant_id=grant_id,
            subject_user_id=subject_user_id,
            accessor_user_id=accessor_user_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            reason=reason,
            timestamp=datetime.now(UTC),
            metadata=metadata or {},
        )
        self.evidence_records[evidence.id] = evidence
        return evidence

    def _invalidate_evaluator_cache(self, subject_user_id: str | None = None, accessor_user_id: str | None = None) -> None:
        try:
            from src.modules.consent_access.evaluator import consent_policy_evaluator

            consent_policy_evaluator.invalidate(subject_user_id=subject_user_id, accessor_user_id=accessor_user_id)
        except Exception:
            # The evaluator may not be loaded in some isolated test scenarios.
            return

    def allowed_scopes(self) -> list[str]:
        scopes: list[str] = []
        for domain, actions in self.scope_catalog.items():
            for action in sorted(actions):
                scopes.append(f"{domain}:{action}")
        return sorted(scopes)

    def _normalize_scopes(self, scopes: list[str]) -> list[str]:
        known = set(self.allowed_scopes())
        normalized = sorted(set(scope.strip().lower() for scope in scopes if scope and scope.strip()))
        unknown = [scope for scope in normalized if scope not in known]
        if unknown:
            raise ValueError(f"Unknown scope(s): {', '.join(unknown)}")
        return normalized

    def request_consent(
        self,
        subject_user_id: str,
        accessor_user_id: str,
        scopes: list[str],
        requested_by_user_id: str,
        request_reason: str | None = None,
        expires_in_days: int = 30,
    ) -> ConsentGrantRecord:
        now = datetime.now(UTC)
        grant = ConsentGrantRecord(
            id=secrets.token_urlsafe(12),
            subject_user_id=subject_user_id,
            accessor_user_id=accessor_user_id,
            scopes=self._normalize_scopes(scopes),
            status=GrantStatus.requested,
            request_reason=request_reason,
            requested_at=now,
            created_at=now,
            expires_at=now + timedelta(days=expires_in_days),
        )
        self.grants[grant.id] = grant
        self._record_evidence(
            grant_id=grant.id,
            subject_user_id=subject_user_id,
            accessor_user_id=accessor_user_id,
            actor_user_id=requested_by_user_id,
            event_type="consent.requested",
            reason=request_reason,
        )
        self._invalidate_evaluator_cache(subject_user_id=subject_user_id, accessor_user_id=accessor_user_id)
        return grant

    def grant_consent(
        self,
        subject_user_id: str,
        accessor_user_id: str,
        scopes: list[str],
        expires_in_days: int = 30,
        actor_user_id: str | None = None,
    ) -> ConsentGrantRecord:
        now = datetime.now(UTC)
        grant = ConsentGrantRecord(
            id=secrets.token_urlsafe(12),
            subject_user_id=subject_user_id,
            accessor_user_id=accessor_user_id,
            scopes=self._normalize_scopes(scopes),
            status=GrantStatus.granted,
            requested_at=now,
            granted_at=now,
            created_at=now,
            expires_at=now + timedelta(days=expires_in_days),
        )
        self.grants[grant.id] = grant
        self._record_evidence(
            grant_id=grant.id,
            subject_user_id=subject_user_id,
            accessor_user_id=accessor_user_id,
            actor_user_id=actor_user_id or subject_user_id,
            event_type="consent.granted",
            reason="direct_grant",
        )
        self._invalidate_evaluator_cache(subject_user_id=subject_user_id, accessor_user_id=accessor_user_id)
        return grant

    def review_consent_request(
        self,
        grant_id: str,
        approve: bool,
        reviewed_by_user_id: str,
        review_notes: str | None = None,
    ) -> ConsentGrantRecord | None:
        grant = self.grants.get(grant_id)
        if not grant:
            return None

        now = datetime.now(UTC)
        grant.reviewed_by_user_id = reviewed_by_user_id
        grant.review_notes = review_notes
        if approve:
            grant.status = GrantStatus.granted
            grant.granted_at = now
            grant.revoked = False
            grant.revoked_at = None
            grant.revoke_reason = None
            event_type = "consent.granted"
        else:
            grant.status = GrantStatus.revoked
            grant.revoked = True
            grant.revoked_at = now
            grant.revoke_reason = review_notes or "request_rejected"
            event_type = "consent.rejected"

        self._record_evidence(
            grant_id=grant.id,
            subject_user_id=grant.subject_user_id,
            accessor_user_id=grant.accessor_user_id,
            actor_user_id=reviewed_by_user_id,
            event_type=event_type,
            reason=review_notes,
        )
        self._invalidate_evaluator_cache(subject_user_id=grant.subject_user_id, accessor_user_id=grant.accessor_user_id)
        return grant

    def revoke_consent(self, grant_id: str, actor_user_id: str | None = None, revoke_reason: str | None = None) -> ConsentGrantRecord | None:
        grant = self.grants.get(grant_id)
        if not grant:
            return None
        grant.status = GrantStatus.revoked
        grant.revoked = True
        grant.revoked_at = datetime.now(UTC)
        grant.revoke_reason = revoke_reason
        self._record_evidence(
            grant_id=grant.id,
            subject_user_id=grant.subject_user_id,
            accessor_user_id=grant.accessor_user_id,
            actor_user_id=actor_user_id or grant.subject_user_id,
            event_type="consent.revoked",
            reason=revoke_reason,
        )
        self._invalidate_evaluator_cache(subject_user_id=grant.subject_user_id, accessor_user_id=grant.accessor_user_id)
        return grant

    def renew_consent(self, grant_id: str, extend_days: int, actor_user_id: str, reason: str | None = None) -> ConsentGrantRecord | None:
        grant = self.grants.get(grant_id)
        if not grant:
            return None
        if grant.status not in {GrantStatus.granted, GrantStatus.expired}:
            return None

        now = datetime.now(UTC)
        anchor = grant.expires_at if grant.expires_at and grant.expires_at > now else now
        grant.expires_at = anchor + timedelta(days=extend_days)
        grant.status = GrantStatus.granted
        grant.revoked = False
        grant.revoked_at = None
        grant.revoke_reason = None
        grant.granted_at = now
        self._record_evidence(
            grant_id=grant.id,
            subject_user_id=grant.subject_user_id,
            accessor_user_id=grant.accessor_user_id,
            actor_user_id=actor_user_id,
            event_type="consent.renewed",
            reason=reason,
            metadata={"extend_days": str(extend_days)},
        )
        self._invalidate_evaluator_cache(subject_user_id=grant.subject_user_id, accessor_user_id=grant.accessor_user_id)
        return grant

    def list_grants(self, subject_user_id: str | None = None, accessor_user_id: str | None = None) -> list[ConsentGrantRecord]:
        items = list(self.grants.values())
        if subject_user_id:
            items = [g for g in items if g.subject_user_id == subject_user_id]
        if accessor_user_id:
            items = [g for g in items if g.accessor_user_id == accessor_user_id]
        return sorted(items, key=lambda g: g.created_at, reverse=True)

    def granted_scopes_for(self, subject_user_id: str, accessor_user_id: str, now: datetime) -> set[str]:
        scopes: set[str] = set()
        for grant in self.grants.values():
            if grant.revoked:
                continue
            if grant.status != GrantStatus.granted:
                continue
            if grant.expires_at and grant.expires_at <= now:
                continue
            if grant.subject_user_id != subject_user_id:
                continue
            if grant.accessor_user_id != accessor_user_id:
                continue
            scopes.update(grant.scopes)
        return scopes

    def active_break_glass_scopes_for(self, actor_user_id: str, subject_user_id: str, now: datetime) -> set[str]:
        scopes: set[str] = set()
        for item in self.break_glass_events.values():
            if item.actor_user_id != actor_user_id:
                continue
            if item.subject_user_id != subject_user_id:
                continue
            if item.expires_at <= now:
                continue
            scopes.update(item.scopes)
        return scopes

    def activate_break_glass(
        self,
        actor_user_id: str,
        subject_user_id: str,
        scopes: list[str],
        reason: str,
        approved_by_user_id: str | None = None,
        duration_minutes: int = 60,
    ) -> BreakGlassAccessRecord:
        now = datetime.now(UTC)
        record = BreakGlassAccessRecord(
            id=secrets.token_urlsafe(10),
            actor_user_id=actor_user_id,
            subject_user_id=subject_user_id,
            scopes=self._normalize_scopes(scopes),
            reason=reason,
            approved_by_user_id=approved_by_user_id,
            started_at=now,
            expires_at=now + timedelta(minutes=max(1, duration_minutes)),
        )
        self.break_glass_events[record.id] = record
        self._record_evidence(
            grant_id=None,
            subject_user_id=subject_user_id,
            accessor_user_id=actor_user_id,
            actor_user_id=actor_user_id,
            event_type="consent.break_glass_activated",
            reason=reason,
            metadata={"duration_minutes": str(duration_minutes)},
        )
        self._invalidate_evaluator_cache(subject_user_id=subject_user_id, accessor_user_id=actor_user_id)
        return record

    def expire_due_grants(self, now: datetime | None = None) -> list[ConsentGrantRecord]:
        now = now or datetime.now(UTC)
        expired: list[ConsentGrantRecord] = []
        for grant in self.grants.values():
            if grant.status != GrantStatus.granted:
                continue
            if not grant.expires_at or grant.expires_at > now:
                continue
            grant.status = GrantStatus.expired
            expired.append(grant)
            self._record_evidence(
                grant_id=grant.id,
                subject_user_id=grant.subject_user_id,
                accessor_user_id=grant.accessor_user_id,
                actor_user_id="system",
                event_type="consent.expired",
                reason="expiry_sweep",
            )
            self._invalidate_evaluator_cache(subject_user_id=grant.subject_user_id, accessor_user_id=grant.accessor_user_id)
        return expired

    def due_for_renewal(self, within_days: int = 3, now: datetime | None = None) -> list[ConsentGrantRecord]:
        now = now or datetime.now(UTC)
        threshold = now + timedelta(days=within_days)
        due: list[ConsentGrantRecord] = []
        for grant in self.grants.values():
            if grant.status != GrantStatus.granted:
                continue
            if not grant.expires_at:
                continue
            if now < grant.expires_at <= threshold:
                due.append(grant)
        return sorted(due, key=lambda item: item.expires_at or datetime.max.replace(tzinfo=UTC))

    def list_evidence(
        self,
        subject_user_id: str | None = None,
        accessor_user_id: str | None = None,
        event_type: str | None = None,
        since: datetime | None = None,
    ) -> list[ConsentEvidenceRecord]:
        items = list(self.evidence_records.values())
        if subject_user_id:
            items = [item for item in items if item.subject_user_id == subject_user_id]
        if accessor_user_id:
            items = [item for item in items if item.accessor_user_id == accessor_user_id]
        if event_type:
            normalized = event_type.strip().lower()
            items = [item for item in items if item.event_type.lower() == normalized]
        if since:
            items = [item for item in items if item.timestamp >= since]
        return sorted(items, key=lambda item: item.timestamp, reverse=True)

    def create_dispute(
        self,
        created_by_user_id: str,
        subject_user_id: str,
        accessor_user_id: str,
        reason: str,
        grant_id: str | None = None,
    ) -> ConsentDisputeRecord:
        now = datetime.now(UTC)
        dispute = ConsentDisputeRecord(
            id=secrets.token_urlsafe(10),
            grant_id=grant_id,
            created_by_user_id=created_by_user_id,
            subject_user_id=subject_user_id,
            accessor_user_id=accessor_user_id,
            reason=reason,
            created_at=now,
        )
        self.disputes[dispute.id] = dispute
        self._record_evidence(
            grant_id=grant_id,
            subject_user_id=subject_user_id,
            accessor_user_id=accessor_user_id,
            actor_user_id=created_by_user_id,
            event_type="consent.dispute.created",
            reason=reason,
            metadata={"dispute_id": dispute.id},
        )
        return dispute

    def resolve_dispute(self, dispute_id: str, resolved_by_user_id: str, resolution_notes: str) -> ConsentDisputeRecord | None:
        dispute = self.disputes.get(dispute_id)
        if not dispute:
            return None
        dispute.status = "resolved"
        dispute.resolution_notes = resolution_notes
        dispute.resolved_by_user_id = resolved_by_user_id
        dispute.resolved_at = datetime.now(UTC)
        self._record_evidence(
            grant_id=dispute.grant_id,
            subject_user_id=dispute.subject_user_id,
            accessor_user_id=dispute.accessor_user_id,
            actor_user_id=resolved_by_user_id,
            event_type="consent.dispute.resolved",
            reason=resolution_notes,
            metadata={"dispute_id": dispute.id},
        )
        return dispute

    def list_disputes(self, only_open: bool = False) -> list[ConsentDisputeRecord]:
        items = list(self.disputes.values())
        if only_open:
            items = [item for item in items if item.status == "open"]
        return sorted(items, key=lambda item: item.created_at, reverse=True)


consent_service = ConsentService()
