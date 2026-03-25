from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import DEMO_USERS, identity_service
from src.main import app
from src.modules.identity_access.service import hash_password

client = TestClient(app)


def _reset_demo_passwords() -> None:
    DEMO_USERS["admin@example.com"].password_hash = hash_password("Admin@123")
    DEMO_USERS["family@example.com"].password_hash = hash_password("Family@123")
    DEMO_USERS["parent@example.com"].password_hash = hash_password("Parent@123")
    DEMO_USERS["caregiver@example.com"].password_hash = hash_password("Caregiver@123")
    DEMO_USERS["doctor@example.com"].password_hash = hash_password("Doctor@123")


def setup_function():
    identity_service.sessions.clear()
    identity_service.revoked_refresh_jtis.clear()
    _reset_demo_passwords()


def teardown_function():
    _reset_demo_passwords()


def _login(email: str, password: str) -> dict:
    payload = {"email": email, "password": password}
    if email in {"admin@example.com", "doctor@example.com"}:
        challenge = client.post("/api/v1/auth/mfa/challenge", json={"username": email})
        assert challenge.status_code == 200
        ticket = challenge.json()
        payload["mfa_ticket"] = ticket["ticket"]
        payload["mfa_code"] = ticket["otp_dev_only"]

    login = client.post("/api/v1/auth/login", json=payload)
    assert login.status_code == 200
    return login.json()


def test_login_with_valid_and_invalid_credentials():
    ok = _login("family@example.com", "Family@123")
    assert ok["token_type"] == "bearer"
    assert ok["role"] == "family_member"

    bad = client.post("/api/v1/auth/login", json={"email": "family@example.com", "password": "wrong"})
    assert bad.status_code == 401


def test_refresh_rotates_token_and_logout_revokes_session():
    login = _login("family@example.com", "Family@123")

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != login["refresh_token"]

    logout = client.post(
        "/api/v1/auth/logout",
        json={"session_id": login["session_id"], "refresh_token": refreshed.json()["refresh_token"]},
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert logout.status_code == 200

    denied = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert denied.status_code == 401


def test_reset_password_flow_with_dev_token():
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "family@example.com",
            "reset_token": "dev-reset-token",
            "new_password": "Family@456",
        },
    )
    assert reset.status_code == 200

    relogin = _login("family@example.com", "Family@456")
    assert relogin["user"]["username"] == "family@example.com"


def test_users_me_requires_auth_and_admin_users_requires_admin_role():
    unauthorized_me = client.get("/api/v1/users/me")
    assert unauthorized_me.status_code == 401

    family_login = _login("family@example.com", "Family@123")
    family_me = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {family_login['access_token']}"},
    )
    assert family_me.status_code == 200
    assert family_me.json()["role"] == "family_member"

    family_denied_admin_users = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {family_login['access_token']}"},
    )
    assert family_denied_admin_users.status_code == 403

    admin_login = _login("admin@example.com", "Admin@123")
    admin_users = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_login['access_token']}"},
    )
    assert admin_users.status_code == 200
    assert admin_users.json()["count"] >= 5
