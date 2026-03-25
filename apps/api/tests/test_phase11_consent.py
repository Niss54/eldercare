from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.audit_logging.store import audit_log_store
from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.consent_access.service import GrantStatus, consent_service

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


def _token_from_headers(headers: dict[str, str]) -> str:
    return headers["Authorization"].split(" ", 1)[1]


def setup_function():
    identity_service.sessions.clear()
    consent_service.grants.clear()
    consent_service.break_glass_events.clear()
    consent_service.evidence_records.clear()
    consent_service.disputes.clear()
    consent_policy_evaluator.invalidate()
    audit_log_store.events.clear()
    audit_log_store.checkpoints.clear()
    audit_log_store.archives.clear()
    audit_log_store.anomalies.clear()


def test_consent_scopes_and_lifecycle_with_evidence():
    parent_headers = _auth_headers("parent@example.com", "Parent@123")

    scopes = client.get("/api/v1/consent/scopes", headers=parent_headers)
    assert scopes.status_code == 200
    assert "health:read" in scopes.json()["items"]
    assert "health:write" in scopes.json()["items"]

    requested = client.post(
        "/api/v1/consent/requests",
        json={
            "subject_user_id": "u_parent",
            "accessor_user_id": "u_doctor",
            "scopes": ["health:read", "health:write"],
            "reason": "Temporary treatment window",
            "expires_in_days": 5,
        },
        headers=parent_headers,
    )
    assert requested.status_code == 200
    request_payload = requested.json()
    assert request_payload["status"] == "requested"

    review = client.post(
        f"/api/v1/consent/requests/{request_payload['id']}/review",
        json={"approve": True, "review_notes": "approved by subject"},
        headers=parent_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "granted"

    revoked = client.delete(
        f"/api/v1/consent/grants/{request_payload['id']}",
        params={"reason": "No longer required"},
        headers=parent_headers,
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    renewable = client.post(
        "/api/v1/consent/grants",
        json={"accessor_user_id": "u_doctor", "scopes": ["health:read"], "expires_in_days": 1},
        headers=parent_headers,
    )
    assert renewable.status_code == 200
    renewable_id = renewable.json()["id"]
    consent_service.grants[renewable_id].expires_at = datetime.now(UTC) - timedelta(minutes=1)
    consent_service.expire_due_grants()

    renewed = client.post(
        f"/api/v1/consent/grants/{renewable_id}/renew",
        json={"extend_days": 7, "reason": "follow-up visits"},
        headers=parent_headers,
    )
    assert renewed.status_code == 200
    assert renewed.json()["status"] == "granted"

    evidence = client.get("/api/v1/consent/evidence", headers=parent_headers)
    assert evidence.status_code == 200
    events = [item["event_type"] for item in evidence.json()["items"]]
    assert "consent.requested" in events
    assert "consent.granted" in events
    assert "consent.revoked" in events
    assert "consent.renewed" in events


def test_policy_evaluator_in_api_and_websocket_with_break_glass_and_expiry_sweep():
    doctor_headers = _auth_headers("doctor@example.com", "Doctor@123")
    parent_headers = _auth_headers("parent@example.com", "Parent@123")
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    denied = client.get(
        "/api/v1/auth/protected/health-read",
        params={"subject_user_id": "u_parent", "scope": "health:read"},
        headers=doctor_headers,
    )
    assert denied.status_code == 403

    emergency = client.post(
        "/api/v1/consent/break-glass",
        json={
            "subject_user_id": "u_parent",
            "scopes": ["health:read"],
            "reason": "Emergency response due to unstable vitals",
            "duration_minutes": 20,
        },
        headers=doctor_headers,
    )
    assert emergency.status_code == 200

    allowed = client.get(
        "/api/v1/auth/protected/health-read",
        params={"subject_user_id": "u_parent", "scope": "health:read"},
        headers=doctor_headers,
    )
    assert allowed.status_code == 200

    events = client.get("/api/v1/audit/events", headers=admin_headers)
    assert events.status_code == 200
    actions = [item["action"] for item in events.json()["items"]]
    assert "consent.break_glass" in actions

    token = _token_from_headers(doctor_headers)
    with client.websocket_connect(f"/ws/notifications?token={token}&subject_user_id=u_parent&scope=health:read") as ws:
        ws.send_text("hello")

    # Create a short-lived grant and verify expiry/renewal sweeps.
    grant = consent_service.grant_consent(
        subject_user_id="u_parent",
        accessor_user_id="u_family",
        scopes=["health:read"],
        expires_in_days=1,
        actor_user_id="u_parent",
    )
    grant.expires_at = datetime.now(UTC) - timedelta(minutes=1)

    expired = consent_service.expire_due_grants()
    assert len(expired) >= 1
    assert any(item.id == grant.id and item.status == GrantStatus.expired for item in expired)

    renewed = consent_service.renew_consent(
        grant_id=grant.id,
        extend_days=2,
        actor_user_id="u_parent",
        reason="renewal requested",
    )
    assert renewed is not None
    assert renewed.status == GrantStatus.granted

    due = consent_service.due_for_renewal(within_days=3)
    assert any(item.id == grant.id for item in due)


def test_dispute_admin_review_tools():
    parent_headers = _auth_headers("parent@example.com", "Parent@123")
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    grant = client.post(
        "/api/v1/consent/grants",
        json={"accessor_user_id": "u_family", "scopes": ["health:read"], "expires_in_days": 3},
        headers=parent_headers,
    )
    assert grant.status_code == 200
    grant_id = grant.json()["id"]

    dispute = client.post(
        "/api/v1/consent/disputes",
        json={
            "subject_user_id": "u_parent",
            "accessor_user_id": "u_family",
            "grant_id": grant_id,
            "reason": "Consent appeared without explicit action",
        },
        headers=parent_headers,
    )
    assert dispute.status_code == 200
    dispute_id = dispute.json()["id"]

    listed = client.get("/api/v1/consent/disputes?open_only=true", headers=admin_headers)
    assert listed.status_code == 200
    assert any(item["id"] == dispute_id for item in listed.json()["items"])

    resolved = client.post(
        f"/api/v1/consent/disputes/{dispute_id}/resolve",
        json={"resolution_notes": "Verified user action with audit timeline"},
        headers=admin_headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
