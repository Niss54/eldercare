from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class FamilyLinkStatus(str, Enum):
    invited = "invited"
    accepted = "accepted"
    rejected = "rejected"
    revoked = "revoked"
    expired = "expired"


class RelationshipType(str, Enum):
    parent = "parent"
    spouse = "spouse"
    child = "child"
    sibling = "sibling"
    caregiver = "caregiver"
    doctor = "doctor"


class Invitation(BaseModel):
    id: str
    email: str
    token: str
    expires_at: datetime
    status: FamilyLinkStatus


class FamilyLink(BaseModel):
    id: str
    family_user_id: str
    parent_user_id: str
    relationship_type: RelationshipType
    status: FamilyLinkStatus
    invited_at: datetime
    decided_at: datetime | None = None
