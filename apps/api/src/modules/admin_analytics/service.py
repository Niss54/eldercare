import csv
import io
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from src.modules.audit_logging.store import audit_log_store
from src.modules.caregiver_marketplace.service import caregiver_marketplace_service
from src.modules.family_parent_linking.service import LinkStatus, family_link_service
from src.modules.medication_reminders.service import medication_reminder_service
from src.modules.notifications.service import notification_service
from src.modules.sos_alerting.service import sos_service
from src.modules.subscriptions.service import subscription_service


class DashboardFilters(BaseModel):
    geography: str | None = None
    role: str | None = None
    plan: str | None = None
    time_window: str | None = None


class FeatureFlagConfig(BaseModel):
    key: str
    enabled: bool
    rollout_percentage: int = 100
    roles: list[str] = Field(default_factory=list)
    plans: list[str] = Field(default_factory=list)
    updated_at: datetime


class AdminActionResult(BaseModel):
    action: str
    status: str
    detail: str
    metadata: dict[str, str] = Field(default_factory=dict)


class AdminAnalyticsService:
    def __init__(self):
        self.disabled_accounts: set[str] = set()
        self.invite_resend_log: list[dict[str, str]] = []
        self.incident_reviews: dict[str, dict[str, str]] = {}
        now = datetime.now(UTC)
        self.feature_flags: dict[str, FeatureFlagConfig] = {
            "admin.dashboard.v2": FeatureFlagConfig(
                key="admin.dashboard.v2",
                enabled=True,
                rollout_percentage=100,
                roles=["admin"],
                plans=["free", "plus", "clinical"],
                updated_at=now,
            ),
            "analytics.export.csv": FeatureFlagConfig(
                key="analytics.export.csv",
                enabled=True,
                rollout_percentage=100,
                roles=["admin"],
                plans=["free", "plus", "clinical"],
                updated_at=now,
            ),
        }

    @staticmethod
    def _time_window_since(time_window: str | None) -> datetime | None:
        if not time_window:
            return None
        now = datetime.now(UTC)
        normalized = time_window.lower()
        if normalized in {"24h", "1d", "day"}:
            return now - timedelta(hours=24)
        if normalized in {"7d", "week"}:
            return now - timedelta(days=7)
        if normalized in {"30d", "month"}:
            return now - timedelta(days=30)
        return None

    def metrics_catalog(self) -> dict[str, list[dict[str, str]]]:
        return {
            "operational": [
                {"key": "queue.pending_medication", "label": "Medication Queue Pending", "owner": "care-ops"},
                {"key": "notifications.failed", "label": "Notification Failures", "owner": "ops"},
                {"key": "sos.open_incidents", "label": "Open SOS Incidents", "owner": "safety"},
                {"key": "audit.anomalies", "label": "Audit Anomalies", "owner": "security"},
            ],
            "product": [
                {"key": "marketplace.bookings_total", "label": "Marketplace Bookings", "owner": "growth"},
                {"key": "subscriptions.active", "label": "Active Subscriptions", "owner": "revenue"},
                {"key": "subscriptions.churn", "label": "Churn Events", "owner": "revenue"},
                {"key": "subscriptions.conversions", "label": "Conversion Events", "owner": "revenue"},
            ],
        }

    def dashboard(self, filters: DashboardFilters | None = None) -> dict:
        caregiver_marketplace_service.seed_if_empty()
        filters = filters or DashboardFilters()

        caregivers = caregiver_marketplace_service.list_caregivers()
        bookings = caregiver_marketplace_service.list_bookings()
        incidents = sos_service.list_incidents()
        plans = subscription_service.list_plans()
        subscriptions = list(subscription_service.subscriptions.values())
        subscription_metrics = subscription_service.conversion_and_churn_metrics()
        notification_metrics = notification_service.metrics()
        medication_metrics = medication_reminder_service.metrics()

        if filters.geography:
            caregivers = [c for c in caregivers if (c.geography or "").lower() == filters.geography.lower()]
        if filters.plan:
            subscriptions = [s for s in subscriptions if s.plan_code.value == filters.plan]

        since = self._time_window_since(filters.time_window)
        audit_events = audit_log_store.list_events(since=since) if since else audit_log_store.list_events()
        anomalies = audit_log_store.list_anomalies()

        queue_health = {
            "medication_pending": medication_metrics["reminders_pending"],
            "notification_failures": notification_metrics["failed"],
            "sos_open_incidents": len([i for i in incidents if i.status.value != "resolved"]),
        }
        alerts: list[dict[str, str]] = []
        if queue_health["medication_pending"] > 5:
            alerts.append({"severity": "warning", "message": "Medication queue backlog above threshold"})
        if queue_health["notification_failures"] > 0:
            alerts.append({"severity": "warning", "message": "Notification failures detected"})
        if len(anomalies) > 0:
            alerts.append({"severity": "critical", "message": "Audit anomalies require review"})

        return {
            "filters_applied": filters.model_dump(),
            "metrics_catalog": self.metrics_catalog(),
            "marketplace": {
                "caregivers_total": len(caregivers),
                "caregivers_approved": len([c for c in caregivers if c.verification_status.value == "approved"]),
                "bookings_total": len(bookings),
            },
            "notifications": notification_metrics,
            "medication": medication_metrics,
            "sos": {
                "incidents_total": len(incidents),
                "incidents_acknowledged": len([i for i in incidents if i.status.value == "acknowledged"]),
            },
            "subscriptions": {
                "plans": [p.model_dump() for p in plans],
                "active_subscriptions": len(subscriptions),
                "plus_subscriptions": len([s for s in subscriptions if s.plan_code.value == "plus"]),
                "conversion_events": subscription_metrics["conversion_events"],
                "churn_events": subscription_metrics["churn_events"],
                "payment_events": subscription_metrics["payment_events"],
                "invoices_total": subscription_metrics["invoices_total"],
            },
            "usage_cards": [
                {"key": "users.disabled", "label": "Disabled Accounts", "value": str(len(self.disabled_accounts))},
                {"key": "audits.window_events", "label": "Audit Events In Window", "value": str(len(audit_events))},
                {"key": "incidents.reviewed", "label": "Incidents Reviewed", "value": str(len(self.incident_reviews))},
            ],
            "alerts": alerts,
            "queue_health": queue_health,
            "feature_flags": [f.model_dump() for f in self.feature_flags.values()],
        }

    def disable_account(self, actor_user_id: str, user_id: str, reason: str) -> AdminActionResult:
        self.disabled_accounts.add(user_id)
        # Lazy import to avoid import cycles.
        from src.interfaces.api.v1.auth import identity_service

        for session in identity_service.sessions.values():
            if session.user_id == user_id:
                session.revoked = True

        audit_log_store.append_event(
            actor_user_id=actor_user_id,
            action="admin.account.disable",
            resource_type="user",
            resource_id=user_id,
            metadata={"reason": reason},
        )
        return AdminActionResult(action="disable_account", status="ok", detail="Account disabled", metadata={"user_id": user_id})

    def resend_invite(self, actor_user_id: str, request_id: str | None = None) -> AdminActionResult:
        target = None
        if request_id:
            target = family_link_service.requests.get(request_id)
        else:
            pending = [req for req in family_link_service.requests.values() if req.status == LinkStatus.pending]
            target = pending[0] if pending else None
        if not target:
            return AdminActionResult(action="resend_invite", status="noop", detail="No pending invitation found")

        self.invite_resend_log.append(
            {
                "request_id": target.id,
                "family_user_id": target.family_user_id,
                "parent_user_id": target.parent_user_id,
                "resent_at": datetime.now(UTC).isoformat(),
            }
        )
        audit_log_store.append_event(
            actor_user_id=actor_user_id,
            action="admin.invite.resend",
            resource_type="family_link_request",
            resource_id=target.id,
            metadata={"family_user_id": target.family_user_id, "parent_user_id": target.parent_user_id},
        )
        return AdminActionResult(
            action="resend_invite",
            status="ok",
            detail="Invitation resent",
            metadata={"request_id": target.id},
        )

    def review_incident(self, actor_user_id: str, incident_id: str, decision: str, notes: str | None = None) -> AdminActionResult:
        incident = sos_service.incidents.get(incident_id)
        if not incident:
            return AdminActionResult(action="incident_review", status="not_found", detail="Incident not found")

        self.incident_reviews[incident_id] = {
            "decision": decision,
            "notes": notes or "",
            "reviewed_at": datetime.now(UTC).isoformat(),
            "reviewed_by": actor_user_id,
        }
        audit_log_store.append_event(
            actor_user_id=actor_user_id,
            action="admin.incident.review",
            resource_type="sos_incident",
            resource_id=incident_id,
            metadata={"decision": decision, "notes": notes or ""},
        )
        return AdminActionResult(action="incident_review", status="ok", detail="Incident review recorded", metadata={"incident_id": incident_id})

    def list_feature_flags(self) -> list[FeatureFlagConfig]:
        return sorted(self.feature_flags.values(), key=lambda item: item.key)

    def set_feature_flag(
        self,
        actor_user_id: str,
        flag_key: str,
        enabled: bool,
        rollout_percentage: int,
        roles: list[str],
        plans: list[str],
    ) -> FeatureFlagConfig:
        flag = FeatureFlagConfig(
            key=flag_key,
            enabled=enabled,
            rollout_percentage=max(0, min(100, rollout_percentage)),
            roles=sorted(set(roles)),
            plans=sorted(set(plans)),
            updated_at=datetime.now(UTC),
        )
        self.feature_flags[flag_key] = flag
        audit_log_store.append_event(
            actor_user_id=actor_user_id,
            action="admin.feature_flag.update",
            resource_type="feature_flag",
            resource_id=flag_key,
            metadata={"enabled": str(enabled).lower(), "rollout_percentage": str(flag.rollout_percentage)},
        )
        return flag

    def export_dashboard(self, fmt: str = "json", filters: DashboardFilters | None = None) -> tuple[str, str]:
        dashboard = self.dashboard(filters=filters)
        if fmt == "json":
            import json

            return "application/json", json.dumps(dashboard, default=str)

        if fmt == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["section", "metric", "value"])
            writer.writerow(["marketplace", "caregivers_total", dashboard["marketplace"]["caregivers_total"]])
            writer.writerow(["marketplace", "bookings_total", dashboard["marketplace"]["bookings_total"]])
            writer.writerow(["subscriptions", "active_subscriptions", dashboard["subscriptions"]["active_subscriptions"]])
            writer.writerow(["subscriptions", "churn_events", dashboard["subscriptions"]["churn_events"]])
            writer.writerow(["sos", "incidents_total", dashboard["sos"]["incidents_total"]])
            writer.writerow(["queue", "medication_pending", dashboard["queue_health"]["medication_pending"]])
            writer.writerow(["queue", "notification_failures", dashboard["queue_health"]["notification_failures"]])
            return "text/csv", output.getvalue()

        raise ValueError("unsupported format")


admin_analytics_service = AdminAnalyticsService()
