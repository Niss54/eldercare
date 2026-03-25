from fastapi.testclient import TestClient
from src.main import app
from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.consent_access.service import consent_service


client = TestClient(app)

MFA_REQUIRED = {"admin@example.com", "doctor@example.com"}


def setup_function():
    consent_service.grants.clear()
    consent_service.break_glass_events.clear()
    consent_service.evidence_records.clear()
    consent_service.disputes.clear()
    consent_policy_evaluator.invalidate()


def _login(username: str, password: str) -> dict:
    payload = {"username": username, "password": password}
    if username in MFA_REQUIRED:
        challenge = client.post("/api/v1/auth/mfa/challenge", json={"username": username})
        assert challenge.status_code == 200
        challenge_payload = challenge.json()
        payload["mfa_ticket"] = challenge_payload["ticket"]
        payload["mfa_code"] = challenge_payload["otp_dev_only"]

    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    return response.json()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_v1_roles_shell():
    response = client.get("/api/v1/auth/roles")
    assert response.status_code == 200
    assert "admin" in response.json()["roles"]


def test_v2_placeholder_shell():
    response = client.get("/api/v2/meta/status")
    assert response.status_code == 200
    assert response.json()["version"] == "v2"


def test_mfa_challenge_and_verify_flow():
    challenge = client.post("/api/v1/auth/mfa/challenge", json={"username": "admin@example.com"})
    assert challenge.status_code == 200
    payload = challenge.json()

    verify = client.post(
        "/api/v1/auth/mfa/verify",
        json={"ticket": payload["ticket"], "code": payload["otp_dev_only"]},
    )
    assert verify.status_code == 200
    assert verify.json()["user"]["role"] == "admin"


def test_login_logout_works_for_all_roles():
    credentials = [
        ("admin@example.com", "Admin@123"),
        ("family@example.com", "Family@123"),
        ("parent@example.com", "Parent@123"),
        ("caregiver@example.com", "Caregiver@123"),
        ("doctor@example.com", "Doctor@123"),
    ]
    for username, password in credentials:
        login = _login(username, password)
        access_token = login["access_token"]

        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me.status_code == 200
        assert me.json()["username"] == username

        logout = client.post(
            "/api/v1/auth/logout",
            json={"session_id": login["session_id"], "refresh_token": login["refresh_token"]},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout.status_code == 200

        refresh_after_logout = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert refresh_after_logout.status_code == 401


def test_refresh_rotates_token_and_invalidates_previous_refresh():
    login = _login("family@example.com", "Family@123")
    first_refresh = login["refresh_token"]

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert refresh_response.status_code == 200
    second_refresh = refresh_response.json()["refresh_token"]
    assert second_refresh != first_refresh

    stale_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert stale_refresh.status_code == 401


def test_protected_route_is_role_gated():
    family_login = _login("family@example.com", "Family@123")
    admin_login = _login("admin@example.com", "Admin@123")

    family_manage = client.get(
        "/api/v1/auth/protected/identity-manage",
        headers={"Authorization": f"Bearer {family_login['access_token']}"},
    )
    assert family_manage.status_code == 403

    admin_manage = client.get(
        "/api/v1/auth/protected/identity-manage",
        headers={"Authorization": f"Bearer {admin_login['access_token']}"},
    )
    assert admin_manage.status_code == 200


def test_consent_policy_evaluation_skeleton_blocks_without_scope():
    caregiver_login = _login("caregiver@example.com", "Caregiver@123")
    parent_login = _login("parent@example.com", "Parent@123")

    denied = client.get(
        "/api/v1/auth/protected/health-read",
        params={"subject_user_id": "u_parent"},
        headers={"Authorization": f"Bearer {caregiver_login['access_token']}"},
    )
    assert denied.status_code == 403

    grant = client.post(
        "/api/v1/consent/grants",
        json={"accessor_user_id": "u_caregiver", "scopes": ["health:read"]},
        headers={"Authorization": f"Bearer {parent_login['access_token']}"},
    )
    assert grant.status_code == 200

    allowed = client.get(
        "/api/v1/auth/protected/health-read",
        params={"subject_user_id": "u_parent"},
        headers={"Authorization": f"Bearer {caregiver_login['access_token']}"},
    )
    assert allowed.status_code == 200
