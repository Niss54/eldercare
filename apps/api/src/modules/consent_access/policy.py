from dataclasses import dataclass
from datetime import datetime

from src.modules.identity_access.models import Role


@dataclass(slots=True)
class ConsentGrant:
    subject_user_id: str
    accessor_user_id: str
    scope: str
    expires_at: datetime


def is_consent_valid(grant: ConsentGrant, now: datetime) -> bool:
    return now < grant.expires_at


@dataclass(slots=True)
class ConsentDecisionInput:
    actor_user_id: str
    actor_role: Role
    subject_user_id: str
    required_scope: str
    granted_scopes: set[str]
    now: datetime


def evaluate_consent_access(request: ConsentDecisionInput) -> bool:
    if request.actor_role == Role.admin:
        return True
    if request.actor_user_id == request.subject_user_id:
        return True

    if request.required_scope in request.granted_scopes:
        return True

    if ":" in request.required_scope:
        domain, _ = request.required_scope.split(":", 1)
        if f"{domain}:*" in request.granted_scopes:
            return True

    return "*:*" in request.granted_scopes
