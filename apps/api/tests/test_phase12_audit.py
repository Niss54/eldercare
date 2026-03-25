from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
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
    audit_log_store.checkpoint_interval = 3


def test_canonical_schema_and_safe_middleware_metadata_capture():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    _ = client.get("/api/v1/auth/me", headers=admin_headers)
    _ = client.get("/api/v1/consent/scopes", headers=admin_headers)

    events = client.get("/api/v1/audit/events", headers=admin_headers)
    assert events.status_code == 200
    assert events.json()["count"] >= 2

    item = events.json()["items"][-1]
    assert "event_type" in item
    assert "category" in item
    assert "severity" in item
    assert "outcome" in item
    assert "request" in item
    assert "query_keys" in item["request"]
    assert "ip_hash" in item["request"]
    assert item["resource_type"] in {"auth", "consent", "audit"}


def test_append_only_chain_checkpoints_and_compliance_queries():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    for _ in range(6):
        response = client.get("/api/v1/auth/me", headers=admin_headers)
        assert response.status_code == 200

    verify = client.get("/api/v1/audit/verify-integrity", headers=admin_headers)
    assert verify.status_code == 200
    assert verify.json()["valid"] is True

    checkpoints = client.get("/api/v1/audit/checkpoints", headers=admin_headers)
    assert checkpoints.status_code == 200
    assert checkpoints.json()["count"] >= 2

    report = client.get("/api/v1/audit/compliance/report", headers=admin_headers)
    assert report.status_code == 200
    assert report.json()["event_count"] >= 1
    assert report.json()["checkpoint_count"] >= 1


def test_anomaly_hooks_and_retention_archive_controls():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")
    family_headers = _auth_headers("family@example.com", "Family@123")

    for _ in range(5):
        denied = client.get("/api/v1/auth/protected/identity-manage", headers=family_headers)
        assert denied.status_code == 403

    incidents = client.get("/api/v1/audit/incidents", headers=admin_headers)
    assert incidents.status_code == 200
    assert incidents.json()["count"] >= 1

    archived = client.post(
        "/api/v1/audit/archive",
        json={"keep_last": 2, "reason": "phase12_test"},
        headers=admin_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] in {"archived", "noop"}

    archives = client.get("/api/v1/audit/archive", headers=admin_headers)
    assert archives.status_code == 200

    retention = client.post(
        "/api/v1/audit/retention/apply",
        json={"days_to_keep": 1},
        headers=admin_headers,
    )
    assert retention.status_code == 200
    assert retention.json()["status"] in {"archived", "noop"}
