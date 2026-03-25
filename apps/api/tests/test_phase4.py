from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.admin_analytics.service import admin_analytics_service
from src.modules.caregiver_marketplace.service import caregiver_marketplace_service
from src.modules.notifications.service import notification_service
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
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    identity_service.sessions.clear()
    caregiver_marketplace_service.caregivers.clear()
    caregiver_marketplace_service.bookings.clear()
    subscription_service.subscriptions.clear()
    subscription_service.invoices.clear()
    subscription_service.payment_events.clear()
    subscription_service.conversion_events.clear()
    notification_service.deliveries.clear()


def test_marketplace_listing_search_match_and_verification_stub():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")
    family_headers = _auth_headers("family@example.com", "Family@123")

    listed = client.get("/api/v1/marketplace/caregivers", headers=family_headers)
    assert listed.status_code == 200
    assert listed.json()["count"] >= 2
    caregiver_id = listed.json()["items"][1]["id"]

    searched = client.get("/api/v1/marketplace/caregivers", params={"query": "Anika"}, headers=family_headers)
    assert searched.status_code == 200
    assert searched.json()["count"] >= 1

    matched = client.post(
        "/api/v1/marketplace/match",
        json={"location": "Bangalore", "required_skills": ["medication"]},
        headers=family_headers,
    )
    assert matched.status_code == 200
    assert matched.json()["count"] >= 1

    submit = client.post(f"/api/v1/marketplace/caregivers/{caregiver_id}/verification-submit", headers=admin_headers)
    assert submit.status_code == 200
    assert submit.json()["verification_status"] == "pending"

    review = client.post(
        f"/api/v1/marketplace/caregivers/{caregiver_id}/verification-review",
        json={"approve": True},
        headers=admin_headers,
    )
    assert review.status_code == 200
    assert review.json()["verification_status"] == "approved"


def test_subscription_entitlement_guard_for_marketplace_booking():
    family_headers = _auth_headers("family@example.com", "Family@123")

    caregivers = client.get("/api/v1/marketplace/caregivers", headers=family_headers)
    assert caregivers.status_code == 200
    approved = next(c for c in caregivers.json()["items"] if c["verification_status"] == "approved")

    denied = client.post(
        "/api/v1/marketplace/bookings",
        json={"caregiver_id": approved["id"], "start_time": "2026-03-25T09:00:00Z"},
        headers=family_headers,
    )
    assert denied.status_code == 403

    set_plan = client.post(
        "/api/v1/subscriptions/set-plan",
        json={"user_id": "u_family", "plan_code": PlanCode.plus.value},
        headers=family_headers,
    )
    assert set_plan.status_code == 200

    allowed = client.post(
        "/api/v1/marketplace/bookings",
        json={"caregiver_id": approved["id"], "start_time": "2026-03-25T09:00:00Z", "notes": "Mobility support"},
        headers=family_headers,
    )
    assert allowed.status_code == 200

    entitlement = client.get(
        "/api/v1/subscriptions/entitlements/check",
        params={"feature": "marketplace.booking"},
        headers=family_headers,
    )
    assert entitlement.status_code == 200
    assert entitlement.json()["enabled"] is True


def test_admin_analytics_dashboard_v1():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    dashboard = client.get("/api/v1/admin-analytics/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200

    payload = dashboard.json()
    assert "marketplace" in payload
    assert "subscriptions" in payload
    assert "notifications" in payload
    assert "medication" in payload
    assert "sos" in payload

    # service object is imported to ensure module load for runtime path
    assert admin_analytics_service is not None
