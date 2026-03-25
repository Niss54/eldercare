from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Scope(str, Enum):
    medical_history = "medical_history"
    medications = "medications"
    appointments = "appointments"
    vitals = "vitals"


class ConsentDecisionType(str, Enum):
    allow = "allow"
    deny = "deny"


class ConsentDecision(BaseModel):
    decision: ConsentDecisionType
    reason: str | None = None


class ConsentGrant(BaseModel):
    id: str
    grantor_id: str
    grantee_id: str
    scopes: list[str] = Field(default_factory=list)
    valid_from: datetime
    valid_to: datetime
    status: str
