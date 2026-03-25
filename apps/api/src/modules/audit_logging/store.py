import hashlib
import json
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class AuditSeverity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class AuditCategory(str, Enum):
    request = "request"
    auth = "auth"
    consent = "consent"
    clinical = "clinical"
    operational = "operational"
    security = "security"


class AuditOutcome(str, Enum):
    success = "success"
    denied = "denied"
    failure = "failure"


class RequestContext(BaseModel):
    method: str | None = None
    path: str | None = None
    query_keys: list[str] = Field(default_factory=list)
    status_code: int | None = None
    ip_hash: str | None = None
    user_agent: str | None = None


class AuditEvent(BaseModel):
    id: str
    timestamp: datetime
    event_type: str = "audit.event"
    category: AuditCategory = AuditCategory.operational
    severity: AuditSeverity = AuditSeverity.info
    outcome: AuditOutcome = AuditOutcome.success
    actor_user_id: str
    actor_role: str | None = None
    action: str
    resource_type: str
    resource_id: str
    domain: str | None = None
    correlation_id: str | None = None
    request: RequestContext = Field(default_factory=RequestContext)
    pii_safe: bool = True
    metadata: dict[str, str] = Field(default_factory=dict)
    previous_hash: str
    event_hash: str


class AuditCheckpoint(BaseModel):
    checkpoint_id: str
    created_at: datetime
    event_index: int
    event_count: int
    chain_tip_hash: str


class AuditArchiveBatch(BaseModel):
    batch_id: str
    created_at: datetime
    reason: str
    event_count: int
    first_event_at: datetime | None = None
    last_event_at: datetime | None = None
    events_hash: str


class AuditAnomaly(BaseModel):
    id: str
    created_at: datetime
    rule: str
    severity: AuditSeverity
    description: str
    related_event_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class AuditLogStore:
    def __init__(self):
        self.events: list[AuditEvent] = []
        self.checkpoints: list[AuditCheckpoint] = []
        self.archives: list[AuditArchiveBatch] = []
        self.anomalies: list[AuditAnomaly] = []
        self.checkpoint_interval = 25

    def _hash_ip(self, raw_ip: str | None) -> str | None:
        if not raw_ip:
            return None
        return hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()[:16]

    def _build_event_hash_payload(self, event: AuditEvent, previous_hash: str) -> str:
        canonical_payload = {
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "category": event.category.value,
            "severity": event.severity.value,
            "outcome": event.outcome.value,
            "actor_user_id": event.actor_user_id,
            "actor_role": event.actor_role,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "domain": event.domain,
            "correlation_id": event.correlation_id,
            "request": event.request.model_dump(),
            "pii_safe": event.pii_safe,
            "metadata": event.metadata,
            "previous_hash": previous_hash,
        }
        return json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))

    def _record_checkpoint_if_needed(self) -> None:
        if not self.events:
            return
        if len(self.events) % self.checkpoint_interval != 0:
            return
        tip = self.events[-1]
        self.checkpoints.append(
            AuditCheckpoint(
                checkpoint_id=f"cp_{len(self.checkpoints) + 1}",
                created_at=datetime.now(UTC),
                event_index=len(self.events) - 1,
                event_count=len(self.events),
                chain_tip_hash=tip.event_hash,
            )
        )

    def _rebuild_indexes(self) -> None:
        self.checkpoints = []
        self.anomalies = []
        for index, event in enumerate(self.events, start=1):
            self._detect_anomalies_for_event(event)
            if index % self.checkpoint_interval == 0:
                self.checkpoints.append(
                    AuditCheckpoint(
                        checkpoint_id=f"cp_{len(self.checkpoints) + 1}",
                        created_at=datetime.now(UTC),
                        event_index=index - 1,
                        event_count=index,
                        chain_tip_hash=event.event_hash,
                    )
                )

    def _rechain_events(self) -> None:
        previous_hash = "GENESIS"
        for event in self.events:
            payload = self._build_event_hash_payload(event, previous_hash=previous_hash)
            event.previous_hash = previous_hash
            event.event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            previous_hash = event.event_hash

    def _detect_anomalies_for_event(self, event: AuditEvent) -> None:
        if event.request.status_code in {401, 403}:
            recent = [
                item
                for item in self.events[-20:]
                if item.actor_user_id == event.actor_user_id and item.request.status_code in {401, 403}
            ]
            if len(recent) >= 5:
                self.anomalies.append(
                    AuditAnomaly(
                        id=f"an_{len(self.anomalies) + 1}",
                        created_at=datetime.now(UTC),
                        rule="repeated_access_denied",
                        severity=AuditSeverity.warning,
                        description="Repeated denied requests detected for actor",
                        related_event_ids=[item.id for item in recent[-5:]],
                        metadata={"actor_user_id": event.actor_user_id},
                    )
                )

        if event.action == "consent.break_glass":
            self.anomalies.append(
                AuditAnomaly(
                    id=f"an_{len(self.anomalies) + 1}",
                    created_at=datetime.now(UTC),
                    rule="break_glass_usage",
                    severity=AuditSeverity.critical,
                    description="Break-glass access activated",
                    related_event_ids=[event.id],
                    metadata={"actor_user_id": event.actor_user_id, "resource_id": event.resource_id},
                )
            )

    def append_event(
        self,
        actor_user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        event_type: str = "audit.event",
        category: AuditCategory = AuditCategory.operational,
        severity: AuditSeverity = AuditSeverity.info,
        outcome: AuditOutcome = AuditOutcome.success,
        actor_role: str | None = None,
        domain: str | None = None,
        correlation_id: str | None = None,
        request: RequestContext | None = None,
        pii_safe: bool = True,
        metadata: dict[str, str] | None = None,
    ) -> AuditEvent:
        metadata = metadata or {}
        previous_hash = self.events[-1].event_hash if self.events else "GENESIS"
        timestamp = datetime.now(UTC)
        request = request or RequestContext()
        stub = AuditEvent(
            id="",
            timestamp=timestamp,
            event_type=event_type,
            category=category,
            severity=severity,
            outcome=outcome,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            domain=domain,
            correlation_id=correlation_id,
            request=request,
            pii_safe=pii_safe,
            metadata=metadata,
            previous_hash=previous_hash,
            event_hash="",
        )
        payload = self._build_event_hash_payload(stub, previous_hash=previous_hash)
        event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        event = stub.model_copy(update={"id": f"ae_{len(self.events) + 1}", "event_hash": event_hash})
        self.events.append(event)
        self._record_checkpoint_if_needed()
        self._detect_anomalies_for_event(event)
        return event

    def publish_domain_event(
        self,
        domain: str,
        action: str,
        actor_user_id: str,
        actor_role: str | None,
        resource_id: str,
        correlation_id: str | None,
        request: RequestContext,
        outcome: AuditOutcome,
        severity: AuditSeverity,
        metadata: dict[str, str] | None = None,
    ) -> AuditEvent:
        return self.append_event(
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            event_type=f"domain.{domain}.event",
            category=AuditCategory.request,
            severity=severity,
            outcome=outcome,
            action=action,
            resource_type=domain,
            resource_id=resource_id,
            domain=domain,
            correlation_id=correlation_id,
            request=request,
            pii_safe=True,
            metadata=metadata,
        )

    def list_events(
        self,
        actor_user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        correlation_id: str | None = None,
        category: AuditCategory | None = None,
        severity: AuditSeverity | None = None,
        outcome: AuditOutcome | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[AuditEvent]:
        items = list(self.events)
        if actor_user_id:
            items = [event for event in items if event.actor_user_id == actor_user_id]
        if action:
            items = [event for event in items if event.action == action]
        if resource_type:
            items = [event for event in items if event.resource_type == resource_type]
        if correlation_id:
            items = [event for event in items if event.correlation_id == correlation_id]
        if category:
            items = [event for event in items if event.category == category]
        if severity:
            items = [event for event in items if event.severity == severity]
        if outcome:
            items = [event for event in items if event.outcome == outcome]
        if since:
            items = [event for event in items if event.timestamp >= since]
        if until:
            items = [event for event in items if event.timestamp <= until]
        return items

    def list_anomalies(self, severity: AuditSeverity | None = None) -> list[AuditAnomaly]:
        items = list(self.anomalies)
        if severity:
            items = [item for item in items if item.severity == severity]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def list_archives(self) -> list[AuditArchiveBatch]:
        return sorted(self.archives, key=lambda item: item.created_at, reverse=True)

    def archive_old_events(self, keep_last: int = 500, reason: str = "retention_policy") -> AuditArchiveBatch | None:
        if len(self.events) <= keep_last:
            return None
        archived_items = self.events[:-keep_last]
        keep_items = self.events[-keep_last:]
        serialized = json.dumps([item.model_dump(mode="json") for item in archived_items], sort_keys=True)
        batch_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        batch = AuditArchiveBatch(
            batch_id=f"arc_{len(self.archives) + 1}",
            created_at=datetime.now(UTC),
            reason=reason,
            event_count=len(archived_items),
            first_event_at=archived_items[0].timestamp if archived_items else None,
            last_event_at=archived_items[-1].timestamp if archived_items else None,
            events_hash=batch_hash,
        )
        self.archives.append(batch)
        self.events = keep_items
        self._rechain_events()
        self._rebuild_indexes()
        return batch

    def apply_retention_policy(self, days_to_keep: int, now: datetime | None = None) -> AuditArchiveBatch | None:
        now = now or datetime.now(UTC)
        threshold = now.timestamp() - (days_to_keep * 24 * 60 * 60)
        old_items = [event for event in self.events if event.timestamp.timestamp() < threshold]
        if not old_items:
            return None
        keep_items = [event for event in self.events if event.timestamp.timestamp() >= threshold]
        serialized = json.dumps([item.model_dump(mode="json") for item in old_items], sort_keys=True)
        batch_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        batch = AuditArchiveBatch(
            batch_id=f"arc_{len(self.archives) + 1}",
            created_at=now,
            reason=f"retention_days:{days_to_keep}",
            event_count=len(old_items),
            first_event_at=old_items[0].timestamp if old_items else None,
            last_event_at=old_items[-1].timestamp if old_items else None,
            events_hash=batch_hash,
        )
        self.archives.append(batch)
        self.events = keep_items
        self._rechain_events()
        self._rebuild_indexes()
        return batch

    def compliance_report(self, since: datetime | None = None, until: datetime | None = None) -> dict[str, object]:
        events = self.list_events(since=since, until=until)
        phi_events = [item for item in events if item.action.startswith("phi.")]
        denied = [item for item in events if item.outcome == AuditOutcome.denied]
        valid, detail = self.verify_chain()
        return {
            "event_count": len(events),
            "phi_event_count": len(phi_events),
            "denied_count": len(denied),
            "anomaly_count": len(self.anomalies),
            "checkpoint_count": len(self.checkpoints),
            "latest_checkpoint": self.checkpoints[-1].model_dump() if self.checkpoints else None,
            "chain_valid": valid,
            "chain_detail": detail,
        }

    def verify_chain(self) -> tuple[bool, str]:
        previous_hash = "GENESIS"
        for index, event in enumerate(self.events):
            payload = self._build_event_hash_payload(event, previous_hash=previous_hash)
            recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if event.previous_hash != previous_hash:
                return False, f"hash link mismatch at index {index}"
            if event.event_hash != recomputed:
                return False, f"event hash mismatch at index {index}"
            previous_hash = event.event_hash
        for checkpoint in self.checkpoints:
            if checkpoint.event_count <= 0 or checkpoint.event_index >= len(self.events):
                continue
            tip = self.events[checkpoint.event_index]
            if checkpoint.chain_tip_hash != tip.event_hash:
                return False, f"checkpoint mismatch at {checkpoint.checkpoint_id}"
        return True, "chain valid"


audit_log_store = AuditLogStore()
