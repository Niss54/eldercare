from enum import Enum
from pydantic import BaseModel


class Role(str, Enum):
    admin = "admin"
    family_member = "family_member"
    parent = "parent"
    caregiver = "caregiver"
    doctor = "doctor"


def can_access_role(required: Role, actor_roles: set[Role]) -> bool:
    return required in actor_roles or Role.admin in actor_roles


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.admin: {
        "identity:read",
        "identity:manage",
        "consent:manage",
        "family:link",
        "family:approve",
        "family:unlink",
        "health:read",
        "health:write",
        "audit:read",
        "medication:manage",
        "medication:read",
        "notification:send",
        "notification:read",
        "sos:trigger",
        "sos:respond",
        "marketplace:read",
        "marketplace:manage",
        "marketplace:verify",
        "subscription:manage",
        "subscription:read",
        "analytics:read",
    },
    Role.family_member: {
        "identity:read",
        "health:read",
        "family:link",
        "family:unlink",
        "medication:manage",
        "medication:read",
        "notification:read",
        "sos:trigger",
        "marketplace:read",
        "subscription:read",
    },
    Role.parent: {
        "identity:read",
        "consent:manage",
        "health:read",
        "family:approve",
        "family:unlink",
        "medication:read",
        "notification:read",
        "sos:trigger",
        "subscription:read",
    },
    Role.caregiver: {
        "identity:read",
        "health:read",
        "medication:manage",
        "medication:read",
        "notification:send",
        "notification:read",
        "sos:respond",
        "marketplace:read",
    },
    Role.doctor: {
        "identity:read",
        "health:read",
        "health:write",
        "medication:read",
        "notification:read",
        "sos:respond",
        "marketplace:read",
    },
}


def role_permissions(role: Role) -> set[str]:
    return ROLE_PERMISSIONS.get(role, set())


class User(BaseModel):
    id: str
    username: str
    full_name: str
    role: Role
    password_hash: str
