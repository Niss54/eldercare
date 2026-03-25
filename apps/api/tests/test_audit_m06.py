from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.audit.application.services import audit_service
from src.modules.audit.domain.models import Action
from src.modules.audit_logging.store import audit_log_store

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
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    identity_service.sessions.clear()
    audit_log_store.events.clear()
    audit_log_store.checkpoints.clear()
    audit_log_store.archives.clear()
    audit_log_store.anomalies.clear()


def test_audit_service_logs_expected_action():
    event = audit_service.log_event(
        user_id="u_admin",
        action=Action.grant,
        resource_type="consent",
        resource_id="grant_123",
    )
    assert event.user_id == "u_admin"
    assert event.action == Action.grant
    assert event.resource_type == "consent"


def test_audit_events_endpoint_supports_user_id_alias_and_action_filter():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    _ = client.get("/api/v1/auth/me", headers=admin_headers)
    _ = client.get("/api/v1/consent/scopes?token=should_not_leak", headers=admin_headers)

    actor_only = client.get(
        "/api/v1/audit/events",
        params={"user_id": "u_admin", "action": "http.get"},
        headers=admin_headers,
    )
    assert actor_only.status_code == 200
    assert actor_only.json()["count"] >= 1

    masked_query_events = [
        item
        for item in actor_only.json()["items"]
        if "query" in item.get("metadata", {}) and "'token': '***'" in item["metadata"]["query"]
    ]
    assert len(masked_query_events) >= 1
