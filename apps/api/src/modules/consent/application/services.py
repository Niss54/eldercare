from datetime import UTC, datetime

from src.modules.consent.domain.models import ConsentGrant, Scope
from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.consent_access.service import consent_service as consent_access_service
from src.modules.identity_access.models import Role

_SCOPE_MAP: dict[str, str] = {
    Scope.medical_history.value: "health:read",
    Scope.medications.value: "medication:read",
    Scope.appointments.value: "health:read",
    Scope.vitals.value: "health:read",
}


class ConsentService:
    """M04.1 application service adapter around the consent access engine."""

    def _normalize_scopes(self, scopes: list[str | Scope]) -> list[str]:
        normalized: list[str] = []
        for scope in scopes:
            raw = scope.value if isinstance(scope, Scope) else str(scope)
            normalized.append(_SCOPE_MAP.get(raw, raw))
        return sorted(set(normalized))

    def _to_domain(self, grant) -> ConsentGrant:
        valid_to = grant.expires_at or datetime.now(UTC)
        return ConsentGrant(
            id=grant.id,
            grantor_id=grant.subject_user_id,
            grantee_id=grant.accessor_user_id,
            scopes=list(grant.scopes),
            valid_from=grant.created_at,
            valid_to=valid_to,
            status=grant.status.value,
        )

    def grant_access(
        self,
        grantor_id: str,
        grantee_id: str,
        scopes: list[str | Scope],
        valid_to: datetime | None = None,
    ) -> ConsentGrant:
        expires_in_days = 30
        if valid_to is not None:
            delta = valid_to - datetime.now(UTC)
            expires_in_days = max(1, int(delta.total_seconds() // 86400) or 1)

        grant = consent_access_service.grant_consent(
            subject_user_id=grantor_id,
            accessor_user_id=grantee_id,
            scopes=self._normalize_scopes(scopes),
            expires_in_days=expires_in_days,
            actor_user_id=grantor_id,
        )
        return self._to_domain(grant)

    def revoke_access(self, grant_id: str) -> ConsentGrant | None:
        revoked = consent_access_service.revoke_consent(grant_id=grant_id)
        if revoked is None:
            return None
        return self._to_domain(revoked)

    def can_access(self, user_id: str, resource_id: str, scope: str | Scope) -> bool:
        normalized_scope = _SCOPE_MAP.get(scope.value if isinstance(scope, Scope) else str(scope), str(scope))
        return consent_policy_evaluator.evaluate(
            actor_user_id=user_id,
            actor_role=Role.parent,
            subject_user_id=resource_id,
            required_scope=normalized_scope,
            now=datetime.now(UTC),
        )


consent_service = ConsentService()
