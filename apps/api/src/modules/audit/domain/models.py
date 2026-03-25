from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Action(str, Enum):
    create = "CREATE"
    read = "READ"
    update = "UPDATE"
    delete = "DELETE"
    grant = "GRANT"
    revoke = "REVOKE"


class AuditEvent(BaseModel):
    user_id: str
    action: Action
    resource_type: str
    resource_id: str
    timestamp: datetime
    metadata: dict[str, str] = Field(default_factory=dict)
