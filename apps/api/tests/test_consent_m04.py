from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.consent.application.services import consent_service as consent_app_service
from src.modules.consent.domain.models import Scope
from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.consent_access.service import consent_service

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
    consent_service.grants.clear()
    consent_service.break_glass_events.clear()
    consent_service.evidence_records.clear()
    consent_service.disputes.clear()
    consent_policy_evaluator.invalidate()


def test_m04_alias_endpoints_and_check_access():
    parent_headers = _auth_headers("parent@example.com", "Parent@123")
    doctor_headers = _auth_headers("doctor@example.com", "Doctor@123")

    granted = client.post(
        "/api/v1/consent/grant",
        json={"accessor_user_id": "u_doctor", "scopes": ["health:read"], "expires_in_days": 7},
        headers=parent_headers,
    )
    assert granted.status_code == 200
    grant_id = granted.json()["id"]

    mine = client.get("/api/v1/consent/grants/mine", headers=parent_headers)
    assert mine.status_code == 200
    assert any(item["id"] == grant_id for item in mine.json()["items"])

    allowed = client.get(
        "/api/v1/consent/check-access",
        params={"subject_user_id": "u_parent", "scope": "health:read"},
        headers=doctor_headers,
    )
    assert allowed.status_code == 200
    assert allowed.json()["allowed"] is True

    revoked = client.post(
        f"/api/v1/consent/grant/{grant_id}/revoke",
        json={"reason": "no longer needed"},
        headers=parent_headers,
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    denied = client.get(
        "/api/v1/consent/check-access",
        params={"subject_user_id": "u_parent", "scope": "health:read"},
        headers=doctor_headers,
    )
    assert denied.status_code == 200
    assert denied.json()["allowed"] is False


def test_m04_application_service_contract():
    grant = consent_app_service.grant_access(
        grantor_id="u_parent",
        grantee_id="u_family",
        scopes=[Scope.medical_history],
    )
    assert grant.grantor_id == "u_parent"
    assert "health:read" in grant.scopes

    assert consent_app_service.can_access(
        user_id="u_family",
        resource_id="u_parent",
        scope=Scope.medical_history,
    ) is True

    revoked = consent_app_service.revoke_access(grant.id)
    assert revoked is not None
    assert revoked.status == "revoked"
