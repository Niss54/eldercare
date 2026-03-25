from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.caregiver_marketplace.service import caregiver_marketplace_service
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
    caregiver_marketplace_service.credentials.clear()
    caregiver_marketplace_service.bookings.clear()
    caregiver_marketplace_service.ratings.clear()
    caregiver_marketplace_service.incident_reports.clear()
    subscription_service.subscriptions.clear()
    subscription_service.invoices.clear()
    subscription_service.payment_events.clear()
    subscription_service.conversion_events.clear()


def test_onboarding_filtering_and_matching_extensions():
    family_headers = _auth_headers("family@example.com", "Family@123")

    onboard = client.post(
        "/api/v1/marketplace/caregivers/onboarding",
        json={
            "full_name": "Asha Menon",
            "skills": ["dementia", "mobility"],
            "location": "Bangalore",
            "availability": "weekday-evenings",
            "languages": ["en", "hi"],
            "geography": "bangalore-east",
            "bio": "Dementia support specialist",
        },
        headers=family_headers,
    )
    assert onboard.status_code == 200
    profile = onboard.json()
    assert profile["verification_status"] == "draft"

    filtered = client.get(
        "/api/v1/marketplace/caregivers",
        params={"language": "hi", "geography": "bangalore-east", "skill": "dementia"},
        headers=family_headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["count"] >= 1

    matched = client.post(
        "/api/v1/marketplace/match",
        json={"location": "Bangalore", "required_skills": ["mobility"], "preferred_language": "hi"},
        headers=family_headers,
    )
    assert matched.status_code == 200
    assert matched.json()["count"] >= 1
    assert "score" in matched.json()["items"][0]
    assert "rationale" in matched.json()["items"][0]


def test_verification_booking_rating_incident_and_moderation_flows():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")
    family_headers = _auth_headers("family@example.com", "Family@123")

    caregivers = client.get("/api/v1/marketplace/caregivers", headers=family_headers)
    assert caregivers.status_code == 200
    caregiver_id = caregivers.json()["items"][0]["id"]

    credential = client.post(
        f"/api/v1/marketplace/caregivers/{caregiver_id}/credentials",
        json={"credential_type": "nursing-license", "document_ref": "doc://license-1", "issuer": "KMC"},
        headers=admin_headers,
    )
    assert credential.status_code == 200
    assert credential.json()["status"] == "submitted"

    review = client.post(
        f"/api/v1/marketplace/caregivers/{caregiver_id}/verification-review",
        json={"approve": True, "notes": "validated"},
        headers=admin_headers,
    )
    assert review.status_code == 200
    assert review.json()["verification_status"] == "approved"

    set_plan = client.post(
        "/api/v1/subscriptions/set-plan",
        json={"user_id": "u_family", "plan_code": PlanCode.plus.value},
        headers=family_headers,
    )
    assert set_plan.status_code == 200

    booking = client.post(
        "/api/v1/marketplace/bookings",
        json={"caregiver_id": caregiver_id, "start_time": "2026-04-01T09:00:00Z", "notes": "Night care"},
        headers=family_headers,
    )
    assert booking.status_code == 200
    assert booking.json()["status"] == "requested"
    booking_id = booking.json()["id"]

    accepted = client.post(
        f"/api/v1/marketplace/bookings/{booking_id}/review",
        json={"accept": True},
        headers=family_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    completed = client.post(f"/api/v1/marketplace/bookings/{booking_id}/complete", headers=family_headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    rating = client.post(
        f"/api/v1/marketplace/caregivers/{caregiver_id}/ratings",
        json={"score": 5, "comment": "Excellent care"},
        headers=family_headers,
    )
    assert rating.status_code == 200
    ratings_list = client.get(f"/api/v1/marketplace/caregivers/{caregiver_id}/ratings", headers=family_headers)
    assert ratings_list.status_code == 200
    assert ratings_list.json()["count"] >= 1

    incident = client.post(
        f"/api/v1/marketplace/caregivers/{caregiver_id}/incidents",
        json={"severity": "high", "description": "Missed check-in"},
        headers=family_headers,
    )
    assert incident.status_code == 200
    report_id = incident.json()["id"]

    moderate = client.post(
        f"/api/v1/marketplace/incidents/{report_id}/moderate",
        json={"action": "warn"},
        headers=admin_headers,
    )
    assert moderate.status_code == 200
    assert moderate.json()["status"] == "reviewed"


def test_extension_hooks_admin_only():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")
    family_headers = _auth_headers("family@example.com", "Family@123")

    denied = client.post(
        "/api/v1/marketplace/extensions",
        json={"pricing_strategy": "surge_v1", "recommendation_strategy": "ml_shadow_v1"},
        headers=family_headers,
    )
    assert denied.status_code == 403

    updated = client.post(
        "/api/v1/marketplace/extensions",
        json={"pricing_strategy": "surge_v1", "recommendation_strategy": "ml_shadow_v1"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["pricing_strategy"] == "surge_v1"

    fetched = client.get("/api/v1/marketplace/extensions", headers=admin_headers)
    assert fetched.status_code == 200
    assert fetched.json()["recommendation_strategy"] == "ml_shadow_v1"
