from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from src.main import app
from src.core.settings import get_settings

client = TestClient(app)


def test_security_headers_present_on_health():
    response = client.get("/health", headers={"Host": "localhost"})
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_trusted_host_blocks_unknown_host():
    response = client.get("/health", headers={"Host": "evil.example.com"})
    assert response.status_code == 400


def _admin_login_with_mfa() -> dict:
    challenge = client.post("/api/v1/auth/mfa/challenge", json={"username": "admin@example.com"})
    assert challenge.status_code == 200
    challenge_payload = challenge.json()
    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin@example.com",
            "password": "Admin@123",
            "mfa_ticket": challenge_payload["ticket"],
            "mfa_code": challenge_payload["otp_dev_only"],
        },
    )
    assert login.status_code == 200
    return login.json()


def test_admin_login_requires_mfa():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin@example.com", "password": "Admin@123"},
    )
    assert response.status_code == 401
    assert "MFA required" in response.json()["detail"]


def test_jwt_tokens_include_kid_for_rotation():
    settings = get_settings()
    login = _admin_login_with_mfa()
    access_header = jose_jwt.get_unverified_header(login["access_token"])
    refresh_header = jose_jwt.get_unverified_header(login["refresh_token"])
    assert access_header["kid"] == settings.jwt_active_kid
    assert refresh_header["kid"] == settings.jwt_refresh_active_kid


def test_csrf_mismatch_blocks_protected_post_when_cookie_is_present():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "family@example.com", "password": "Family@123"},
        headers={"x-csrf-token": "wrong"},
        cookies={"csrf_token": "expected"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token mismatch"


def test_audit_integrity_endpoint_reports_valid_chain():
    login = _admin_login_with_mfa()
    token = login["access_token"]

    _ = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    verify = client.get("/api/v1/audit/verify-integrity", headers={"Authorization": f"Bearer {token}"})

    assert verify.status_code == 200
    assert verify.json()["valid"] is True
