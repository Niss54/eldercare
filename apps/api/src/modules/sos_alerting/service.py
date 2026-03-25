import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from src.modules.audit_logging.store import audit_log_store
from src.modules.notifications.service import DeliveryMode, NotificationChannel, NotificationPriority, notification_service
from src.modules.realtime.service import realtime_service


class IncidentStatus(str, Enum):
    created = "created"
    escalated = "escalated"
    acknowledged = "acknowledged"
    resolved = "resolved"


class EscalationHop(BaseModel):
    level: int
    recipients: list[str]
    target_roles: list[str] = Field(default_factory=list)
    delay_seconds: int
    retry_delay_seconds: int = 60
    max_retries: int = 2
    retries_attempted: int = 0
    fallback_recipients: list[str] = Field(default_factory=list)
    fallback_roles: list[str] = Field(default_factory=list)
    acknowledged: bool = False
    timed_out: bool = False
    next_attempt_at: datetime
    notified_at: datetime


class TimelineEvent(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    detail: str
    metadata: dict[str, str] = Field(default_factory=dict)


class ResponderProfile(BaseModel):
    user_id: str
    role: str
    available_day: bool = True
    available_night: bool = True


class SosIncident(BaseModel):
    id: str
    subject_user_id: str
    initiated_by_user_id: str
    status: IncidentStatus
    severity: str
    created_at: datetime
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    escalation_hops: list[EscalationHop] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)


class SimulationResult(BaseModel):
    scenario: str
    incident_id: str
    final_status: IncidentStatus
    hops_attempted: int
    total_retries: int
    fallback_invoked: bool
    timeline_events: int


class SosService:
    def __init__(self):
        self.incidents: dict[str, SosIncident] = {}
        self.responder_profiles: list[ResponderProfile] = [
            ResponderProfile(user_id="u_family", role="family_member", available_day=True, available_night=True),
            ResponderProfile(user_id="u_caregiver", role="caregiver", available_day=True, available_night=False),
            ResponderProfile(user_id="u_doctor", role="doctor", available_day=True, available_night=True),
            ResponderProfile(user_id="u_admin", role="admin", available_day=True, available_night=True),
        ]

    @staticmethod
    def _is_daytime(now: datetime) -> bool:
        return 7 <= now.hour < 21

    def _select_recipients(self, target_roles: list[str], now: datetime) -> list[str]:
        if not target_roles:
            return []
        is_day = self._is_daytime(now)
        selected: list[str] = []
        for role in target_roles:
            role_matches = [
                p for p in self.responder_profiles if p.role == role and ((p.available_day and is_day) or (p.available_night and not is_day))
            ]
            if role_matches:
                selected.append(role_matches[0].user_id)
        return selected

    def _append_timeline(
        self,
        incident: SosIncident,
        event_type: str,
        detail: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        event = TimelineEvent(
            id=secrets.token_urlsafe(10),
            timestamp=datetime.now(UTC),
            event_type=event_type,
            detail=detail,
            metadata=metadata or {},
        )
        incident.timeline.append(event)

    def _emit_audit(self, actor_user_id: str, incident: SosIncident, action: str, metadata: dict[str, str] | None = None) -> None:
        audit_log_store.append_event(
            actor_user_id=actor_user_id,
            action=action,
            resource_type="sos_incident",
            resource_id=incident.id,
            metadata=metadata or {},
        )

    def _dispatch_parallel_notifications(self, incident: SosIncident, recipients: list[str], message: str) -> None:
        for recipient in recipients:
            notification_service.send(
                recipient_user_id=recipient,
                channels=[NotificationChannel.sms, NotificationChannel.push, NotificationChannel.in_app],
                message=message,
                priority=NotificationPriority.critical,
                dedup_key=f"sos:{incident.id}:{recipient}:{len(incident.timeline)}",
                mode=DeliveryMode.fanout,
            )

    def trigger_incident(
        self,
        subject_user_id: str,
        initiated_by_user_id: str,
        severity: str,
        cascade: list[dict],
        triggered_at: datetime | None = None,
    ) -> SosIncident:
        now = triggered_at or datetime.now(UTC)
        incident = SosIncident(
            id=secrets.token_urlsafe(12),
            subject_user_id=subject_user_id,
            initiated_by_user_id=initiated_by_user_id,
            status=IncidentStatus.created,
            severity=severity,
            created_at=now,
            escalation_hops=[],
        )
        self.incidents[incident.id] = incident
        self._append_timeline(incident, "incident.created", "SOS incident created", {"severity": severity})
        self._emit_audit(initiated_by_user_id, incident, "sos.created", {"severity": severity})

        for level, hop in enumerate(cascade, start=1):
            target_roles = [str(role) for role in hop.get("target_roles", [])]
            recipients = [str(user) for user in hop.get("recipients", [])]
            if not recipients:
                recipients = self._select_recipients(target_roles=target_roles, now=now)

            delay_seconds = int(hop.get("delay_seconds", 0))
            retry_delay_seconds = int(hop.get("retry_delay_seconds", 60))
            max_retries = int(hop.get("max_retries", 2))
            fallback_recipients = [str(user) for user in hop.get("fallback_recipients", [])]
            fallback_roles = [str(role) for role in hop.get("fallback_roles", [])]

            hop_record = EscalationHop(
                level=level,
                recipients=recipients,
                target_roles=target_roles,
                delay_seconds=delay_seconds,
                retry_delay_seconds=retry_delay_seconds,
                max_retries=max_retries,
                fallback_recipients=fallback_recipients,
                fallback_roles=fallback_roles,
                next_attempt_at=now + timedelta(seconds=delay_seconds),
                notified_at=now,
            )
            incident.escalation_hops.append(hop_record)
            self._dispatch_parallel_notifications(
                incident=incident,
                recipients=recipients,
                message=f"SOS incident {incident.id} requires acknowledgement",
            )
            self._append_timeline(
                incident,
                "incident.escalation_dispatched",
                f"Escalation level {level} dispatched",
                {
                    "recipients": ",".join(recipients),
                    "target_roles": ",".join(target_roles),
                    "delay_seconds": str(delay_seconds),
                },
            )

        incident.status = IncidentStatus.escalated if incident.escalation_hops else IncidentStatus.created
        self._emit_audit(initiated_by_user_id, incident, "sos.escalated", {"hops": str(len(incident.escalation_hops))})
        realtime_service.publish(
            channel="sos",
            event_type="sos.triggered",
            payload={"incident_id": incident.id, "subject_user_id": subject_user_id, "severity": severity},
        )
        return incident

    def process_escalation_tick(self, incident_id: str, now: datetime | None = None, network_outage: bool = False) -> SosIncident:
        now = now or datetime.now(UTC)
        incident = self.incidents.get(incident_id)
        if not incident:
            raise ValueError("incident not found")
        if incident.status in {IncidentStatus.acknowledged, IncidentStatus.resolved}:
            return incident

        for hop in incident.escalation_hops:
            if hop.acknowledged or hop.timed_out:
                continue
            if now < hop.next_attempt_at:
                continue

            if hop.retries_attempted < hop.max_retries:
                hop.retries_attempted += 1
                hop.notified_at = now
                hop.next_attempt_at = now + timedelta(seconds=hop.retry_delay_seconds)
                channels = [NotificationChannel.in_app] if network_outage else [NotificationChannel.sms, NotificationChannel.push, NotificationChannel.in_app]
                for recipient in hop.recipients:
                    notification_service.send(
                        recipient_user_id=recipient,
                        channels=channels,
                        message=f"SOS incident {incident.id} escalation retry {hop.retries_attempted}",
                        priority=NotificationPriority.critical,
                        dedup_key=f"sos-retry:{incident.id}:{hop.level}:{hop.retries_attempted}:{recipient}",
                        mode=DeliveryMode.fanout,
                    )
                self._append_timeline(
                    incident,
                    "incident.escalation_retry",
                    f"Escalation level {hop.level} retried",
                    {"retry": str(hop.retries_attempted), "network_outage": str(network_outage).lower()},
                )
                self._emit_audit(
                    actor_user_id=incident.initiated_by_user_id,
                    incident=incident,
                    action="sos.retry",
                    metadata={"level": str(hop.level), "retry": str(hop.retries_attempted)},
                )
                continue

            fallback_recipients = list(hop.fallback_recipients)
            if hop.fallback_roles:
                fallback_recipients.extend(self._select_recipients(hop.fallback_roles, now))
            fallback_recipients = sorted(set(fallback_recipients))

            if fallback_recipients:
                self._dispatch_parallel_notifications(
                    incident,
                    fallback_recipients,
                    f"SOS incident {incident.id} fallback escalation activated",
                )
                self._append_timeline(
                    incident,
                    "incident.fallback_invoked",
                    f"Fallback dispatched for level {hop.level}",
                    {"recipients": ",".join(fallback_recipients)},
                )
                self._emit_audit(
                    actor_user_id=incident.initiated_by_user_id,
                    incident=incident,
                    action="sos.fallback",
                    metadata={"level": str(hop.level), "recipients": ",".join(fallback_recipients)},
                )
            else:
                hop.timed_out = True
                self._append_timeline(
                    incident,
                    "incident.escalation_timeout",
                    f"Escalation level {hop.level} timed out with no fallback",
                )
                self._emit_audit(
                    actor_user_id=incident.initiated_by_user_id,
                    incident=incident,
                    action="sos.timeout",
                    metadata={"level": str(hop.level)},
                )

        if any(not hop.acknowledged for hop in incident.escalation_hops):
            incident.status = IncidentStatus.escalated
            realtime_service.publish(
                channel="sos",
                event_type="sos.escalation_updated",
                payload={"incident_id": incident.id, "status": incident.status.value},
            )
        return incident

    def acknowledge(self, incident_id: str, responder_user_id: str) -> SosIncident:
        incident = self.incidents.get(incident_id)
        if not incident:
            raise ValueError("incident not found")
        incident.status = IncidentStatus.acknowledged
        incident.acknowledged_by = responder_user_id
        incident.acknowledged_at = datetime.now(UTC)
        for hop in incident.escalation_hops:
            if responder_user_id in hop.recipients or responder_user_id in hop.fallback_recipients:
                hop.acknowledged = True
        self._append_timeline(incident, "incident.acknowledged", "Incident acknowledged", {"responder": responder_user_id})
        self._emit_audit(responder_user_id, incident, "sos.acknowledged", {"responder": responder_user_id})
        realtime_service.publish(
            channel="sos",
            event_type="sos.acknowledged",
            payload={"incident_id": incident.id, "responder_user_id": responder_user_id},
        )
        return incident

    def resolve(self, incident_id: str, resolver_user_id: str) -> SosIncident:
        incident = self.incidents.get(incident_id)
        if not incident:
            raise ValueError("incident not found")
        incident.status = IncidentStatus.resolved
        incident.resolved_by = resolver_user_id
        incident.resolved_at = datetime.now(UTC)
        self._append_timeline(incident, "incident.resolved", "Incident resolved", {"resolver": resolver_user_id})
        self._emit_audit(resolver_user_id, incident, "sos.resolved", {"resolver": resolver_user_id})
        realtime_service.publish(
            channel="sos",
            event_type="sos.resolved",
            payload={"incident_id": incident.id, "resolver_user_id": resolver_user_id},
        )
        return incident

    def forensic_timeline(self, incident_id: str) -> list[TimelineEvent]:
        incident = self.incidents.get(incident_id)
        if not incident:
            raise ValueError("incident not found")
        return list(incident.timeline)

    def simulate_scenario(self, scenario: str) -> SimulationResult:
        now = datetime.now(UTC)
        if scenario not in {"day", "night", "network_outage"}:
            raise ValueError("unsupported scenario")

        scenario_hour = 14 if scenario == "day" else 2
        simulated_now = now.replace(hour=scenario_hour, minute=0, second=0, microsecond=0)
        if simulated_now <= now:
            simulated_now = simulated_now + timedelta(days=1)

        incident = self.trigger_incident(
            subject_user_id="u_parent",
            initiated_by_user_id="u_family",
            severity="critical",
            cascade=[
                {"target_roles": ["caregiver"], "delay_seconds": 0, "max_retries": 1, "retry_delay_seconds": 30},
                {
                    "target_roles": ["doctor"],
                    "delay_seconds": 30,
                    "max_retries": 1,
                    "retry_delay_seconds": 30,
                    "fallback_roles": ["admin"],
                },
            ],
            triggered_at=simulated_now,
        )

        # Force retries/escalations by advancing time.
        self.process_escalation_tick(
            incident_id=incident.id,
            now=simulated_now + timedelta(seconds=90),
            network_outage=(scenario == "network_outage"),
        )
        if scenario == "day":
            self.acknowledge(incident.id, "u_doctor")
        if scenario == "night":
            self.process_escalation_tick(incident.id, now=simulated_now + timedelta(seconds=180), network_outage=False)

        fallback_invoked = any(event.event_type == "incident.fallback_invoked" for event in incident.timeline)
        total_retries = sum(hop.retries_attempted for hop in incident.escalation_hops)

        return SimulationResult(
            scenario=scenario,
            incident_id=incident.id,
            final_status=incident.status,
            hops_attempted=len(incident.escalation_hops),
            total_retries=total_retries,
            fallback_invoked=fallback_invoked,
            timeline_events=len(incident.timeline),
        )

    def list_incidents(self) -> list[SosIncident]:
        return sorted(self.incidents.values(), key=lambda i: i.created_at, reverse=True)


sos_service = SosService()
