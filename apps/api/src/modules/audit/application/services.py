from datetime import UTC, datetime

from src.modules.audit.domain.models import Action, AuditEvent
from src.modules.audit_logging.store import audit_log_store

_ACTION_MAP: dict[Action, str] = {
    Action.create: "create",
    Action.read: "read",
    Action.update: "update",
    Action.delete: "delete",
    Action.grant: "grant",
    Action.revoke: "revoke",
}


class AuditService:
    """M06.1 service layer for append-only audit logging operations."""

    def log_event(self, user_id: str, action: Action, resource_type: str, resource_id: str) -> AuditEvent:
        logged = audit_log_store.append_event(
            actor_user_id=user_id,
            action=_ACTION_MAP[action],
            resource_type=resource_type,
            resource_id=resource_id,
            metadata={"source": "m06.audit_service"},
        )
        return AuditEvent(
            user_id=logged.actor_user_id,
            action=action,
            resource_type=logged.resource_type,
            resource_id=logged.resource_id,
            timestamp=logged.timestamp,
            metadata=dict(logged.metadata),
        )


audit_service = AuditService()
