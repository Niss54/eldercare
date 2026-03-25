from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.admin_analytics.service import FeatureFlagConfig, admin_analytics_service
from src.modules.audit_logging.store import audit_log_store
from src.modules.family_parent_linking.service import family_link_service
from src.modules.notifications.service import notification_service
from src.modules.sos_alerting.service import sos_service
from src.modules.subscriptions.service import PlanCode, subscription_service

client = TestClient(app)

MFA_REQUIRED = {"admin@example.com", "doctor@example.com"}


def _auth_headers(username: str, password: str) -> dict[str, str]:
    payload = {"username": username, "password": password}
    if username in MFA_REQUIRED:
        challenge = client.post("/api/v1/auth/mfa/challenge", json={"username": username})
        assert challenge.status_code == 200
        challenge_payload = challenge.json()
        payload["mfa_ticket"] = challenge_payload["ticket"]
        payload["mfa_code"] = challenge_payload["otp_dev_only"]

    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def setup_function():
    identity_service.sessions.clear()
    family_link_service.requests.clear()
    family_link_service.links.clear()
    sos_service.incidents.clear()
    notification_service.deliveries.clear()

    subscription_service.subscriptions.clear()
    subscription_service.invoices.clear()
    subscription_service.payment_events.clear()
    subscription_service.conversion_events.clear()

    audit_log_store.events.clear()
    audit_log_store.checkpoints.clear()
    audit_log_store.archives.clear()
    audit_log_store.anomalies.clear()

    admin_analytics_service.disabled_accounts.clear()
    admin_analytics_service.invite_resend_log.clear()
    admin_analytics_service.incident_reviews.clear()
    now = datetime.now(UTC)
    admin_analytics_service.feature_flags = {
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


def test_dashboard_catalog_and_filters_with_admin_only_guard():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")
    family_headers = _auth_headers("family@example.com", "Family@123")

    denied = client.get("/api/v1/admin-analytics/dashboard", headers=family_headers)
    assert denied.status_code == 403

    grant_plus = client.post(
        "/api/v1/subscriptions/set-plan",
        json={"user_id": "u_family", "plan_code": PlanCode.plus.value},
        headers=family_headers,
    )
    assert grant_plus.status_code == 200

    dashboard = client.get(
        "/api/v1/admin-analytics/dashboard",
        params={"plan": "plus", "time_window": "7d", "geography": "bangalore"},
        headers=admin_headers,
    )
    assert dashboard.status_code == 200

    payload = dashboard.json()
    assert payload["filters_applied"]["plan"] == "plus"
    assert payload["metrics_catalog"]["operational"]
    assert payload["usage_cards"]
    assert "queue_health" in payload

    catalog = client.get("/api/v1/admin-analytics/metrics/catalog", headers=admin_headers)
    assert catalog.status_code == 200
    assert catalog.json()["product"]


def test_operational_actions_disable_resend_and_incident_review():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")
    family_headers = _auth_headers("family@example.com", "Family@123")

    # Create a pending family-parent link request for resend action coverage.
    create_request = client.post(
        "/api/v1/family-links/requests",
        json={"parent_user_id": "u_parent"},
        headers=family_headers,
    )
    assert create_request.status_code == 200
    request_id = create_request.json()["id"]

    resend = client.post(
        "/api/v1/admin-analytics/actions/resend-invite",
        json={"request_id": request_id},
        headers=admin_headers,
    )
    assert resend.status_code == 200
    assert resend.json()["status"] == "ok"

    trigger = client.post(
        "/api/v1/sos/incidents/trigger",
        json={"subject_user_id": "u_parent", "severity": "critical"},
        headers=family_headers,
    )
    assert trigger.status_code == 200
    incident_id = trigger.json()["id"]

    review = client.post(
        "/api/v1/admin-analytics/actions/incident-review",
        json={"incident_id": incident_id, "decision": "close-monitor", "notes": "Escalation policy followed."},
        headers=admin_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "ok"

    disable = client.post(
        "/api/v1/admin-analytics/actions/disable-account",
        json={"user_id": "u_family", "reason": "Repeated suspicious login patterns"},
        headers=admin_headers,
    )
    assert disable.status_code == 200
    assert disable.json()["action"] == "disable_account"

    # The family member session should be revoked after disable-account action.
    me = client.get("/api/v1/auth/me", headers=family_headers)
    assert me.status_code == 401


def test_export_reports_and_feature_flag_controls():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    export_json = client.get("/api/v1/admin-analytics/reports/export", headers=admin_headers)
    assert export_json.status_code == 200
    assert export_json.headers["content-type"].startswith("application/json")

    export_csv = client.get(
        "/api/v1/admin-analytics/reports/export",
        params={"format": "csv", "time_window": "24h"},
        headers=admin_headers,
    )
    assert export_csv.status_code == 200
    assert export_csv.headers["content-type"].startswith("text/csv")
    assert "section,metric,value" in export_csv.text

    bad_export = client.get(
        "/api/v1/admin-analytics/reports/export",
        params={"format": "xml"},
        headers=admin_headers,
    )
    assert bad_export.status_code == 400

    list_flags = client.get("/api/v1/admin-analytics/feature-flags", headers=admin_headers)
    assert list_flags.status_code == 200
    assert list_flags.json()["count"] >= 2

    update_flag = client.post(
        "/api/v1/admin-analytics/feature-flags/rollout.new.queue",
        json={
            "enabled": True,
            "rollout_percentage": 20,
            "roles": ["admin", "admin"],
            "plans": ["plus", "clinical", "plus"],
        },
        headers=admin_headers,
    )
    assert update_flag.status_code == 200
    body = update_flag.json()
    assert body["key"] == "rollout.new.queue"
    assert body["rollout_percentage"] == 20
    assert body["roles"] == ["admin"]
    assert body["plans"] == ["clinical", "plus"]
