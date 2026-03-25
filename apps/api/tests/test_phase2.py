from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.audit_logging.store import audit_log_store
from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.consent_access.service import consent_service
from src.modules.family_parent_linking.service import family_link_service
from src.modules.health_records.service import health_record_service

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


def _grant(subject_headers: dict[str, str], accessor_user_id: str, scopes: list[str]) -> None:
    response = client.post(
        "/api/v1/consent/grants",
        json={"accessor_user_id": accessor_user_id, "scopes": scopes, "expires_in_days": 30},
        headers=subject_headers,
    )
    assert response.status_code == 200


def setup_function():
    identity_service.sessions.clear()
    consent_service.grants.clear()
    consent_service.break_glass_events.clear()
    consent_service.evidence_records.clear()
    consent_service.disputes.clear()
    consent_policy_evaluator.invalidate()
    family_link_service.requests.clear()
    family_link_service.links.clear()
    health_record_service.records.clear()
    audit_log_store.events.clear()
    audit_log_store.checkpoints.clear()
    audit_log_store.archives.clear()
    audit_log_store.anomalies.clear()


def test_family_member_link_approve_unlink_workflow():
    family_headers = _auth_headers("family@example.com", "Family@123")
    parent_headers = _auth_headers("parent@example.com", "Parent@123")

    create_request = client.post(
        "/api/v1/family-links/requests",
        json={"parent_user_id": "u_parent"},
        headers=family_headers,
    )
    assert create_request.status_code == 200
    request_id = create_request.json()["id"]

    approve = client.post(f"/api/v1/family-links/requests/{request_id}/approve", headers=parent_headers)
    assert approve.status_code == 200
    assert approve.json()["family_user_id"] == "u_family"

    links = client.get("/api/v1/family-links/links/me", headers=family_headers)
    assert links.status_code == 200
    assert links.json()["count"] == 1

    unlink = client.delete("/api/v1/family-links/links/u_family/u_parent", headers=family_headers)
    assert unlink.status_code == 200

    links_after = client.get("/api/v1/family-links/links/me", headers=family_headers)
    assert links_after.status_code == 200
    assert links_after.json()["count"] == 0


def test_family_link_request_tracks_relationship_and_pending_invitations():
    family_headers = _auth_headers("family@example.com", "Family@123")
    parent_headers = _auth_headers("parent@example.com", "Parent@123")

    create_request = client.post(
        "/api/v1/family-links/requests",
        json={"parent_user_id": "u_parent", "relationship_type": "spouse"},
        headers=family_headers,
    )
    assert create_request.status_code == 200
    payload = create_request.json()
    assert payload["relationship_type"] == "spouse"
    assert payload["invitation_token"]

    pending = client.get("/api/v1/family-links/invitations/pending", headers=parent_headers)
    assert pending.status_code == 200
    assert pending.json()["count"] == 1
    assert pending.json()["items"][0]["id"] == payload["id"]

    approve = client.post(f"/api/v1/family-links/requests/{payload['id']}/approve", headers=parent_headers)
    assert approve.status_code == 200
    assert approve.json()["relationship_type"] == "spouse"

    network = client.get("/api/v1/family-links/network", headers=family_headers)
    assert network.status_code == 200
    assert network.json()["count"] == 1
    assert network.json()["items"][0]["relationship_type"] == "spouse"


def test_expired_family_invitation_cannot_be_approved():
    family_headers = _auth_headers("family@example.com", "Family@123")
    parent_headers = _auth_headers("parent@example.com", "Parent@123")

    create_request = client.post(
        "/api/v1/family-links/requests",
        json={"parent_user_id": "u_parent", "relationship_type": "parent"},
        headers=family_headers,
    )
    assert create_request.status_code == 200
    request_id = create_request.json()["id"]

    target = family_link_service.requests[request_id]
    target.expires_at = datetime.now(UTC) - timedelta(seconds=1)

    approve = client.post(f"/api/v1/family-links/requests/{request_id}/approve", headers=parent_headers)
    assert approve.status_code == 400
    assert "already decided" in approve.json()["detail"]

    refreshed = client.get("/api/v1/family-links/requests", headers=family_headers)
    assert refreshed.status_code == 200
    current = [item for item in refreshed.json()["items"] if item["id"] == request_id][0]
    assert current["status"] == "expired"


def test_health_records_require_valid_consent():
    doctor_headers = _auth_headers("doctor@example.com", "Doctor@123")
    parent_headers = _auth_headers("parent@example.com", "Parent@123")
    family_headers = _auth_headers("family@example.com", "Family@123")

    denied_write = client.post(
        "/api/v1/health-records/",
        json={"subject_user_id": "u_parent", "data_type": "bp", "summary": "120/80"},
        headers=doctor_headers,
    )
    assert denied_write.status_code == 403

    _grant(parent_headers, accessor_user_id="u_doctor", scopes=["health:write", "health:read"])

    created = client.post(
        "/api/v1/health-records/",
        json={"subject_user_id": "u_parent", "data_type": "bp", "summary": "120/80"},
        headers=doctor_headers,
    )
    assert created.status_code == 200
    record_id = created.json()["id"]

    denied_read = client.get(f"/api/v1/health-records/{record_id}", headers=family_headers)
    assert denied_read.status_code == 403

    _grant(parent_headers, accessor_user_id="u_family", scopes=["health:read"])

    allowed_read = client.get(f"/api/v1/health-records/{record_id}", headers=family_headers)
    assert allowed_read.status_code == 200


def test_phi_reads_and_writes_emit_immutable_audit_chain():
    doctor_headers = _auth_headers("doctor@example.com", "Doctor@123")
    parent_headers = _auth_headers("parent@example.com", "Parent@123")
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    _grant(parent_headers, accessor_user_id="u_doctor", scopes=["health:write", "health:read"])

    created = client.post(
        "/api/v1/health-records/",
        json={"subject_user_id": "u_parent", "data_type": "note", "summary": "Medication updated"},
        headers=doctor_headers,
    )
    assert created.status_code == 200
    record_id = created.json()["id"]

    fetched = client.get(f"/api/v1/health-records/{record_id}", headers=doctor_headers)
    assert fetched.status_code == 200

    audit_response = client.get("/api/v1/audit/events", headers=admin_headers)
    assert audit_response.status_code == 200
    events = audit_response.json()["items"]
    assert len(events) >= 2

    previous_hash = "GENESIS"
    for event in events:
        assert event["previous_hash"] == previous_hash
        previous_hash = event["event_hash"]
