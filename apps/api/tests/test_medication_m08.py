from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.medication_reminders.service import medication_reminder_service

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
    medication_reminder_service.schedules.clear()
    medication_reminder_service.reminders.clear()
    medication_reminder_service.dispatch_history.clear()
    medication_reminder_service.adherence_records.clear()


def test_m08_recurring_schedule_and_adherence_tracking_flow():
    family_headers = _auth_headers("family@example.com", "Family@123")

    schedule = client.post(
        "/api/v1/medication/schedules",
        json={
            "subject_user_id": "u_parent",
            "medication_name": "Metformin",
            "dosage": "500mg",
            "reminder_message": "Take Metformin",
            "interval_minutes": 60,
            "start_at": (datetime.now(UTC) - timedelta(minutes=2)).isoformat(),
        },
        headers=family_headers,
    )
    assert schedule.status_code == 200
    assert schedule.json()["interval_minutes"] == 60

    queued = client.post("/api/v1/medication/queue-due", headers=family_headers)
    assert queued.status_code == 200
    assert queued.json()["queued"] == 1
    reminder_id = queued.json()["items"][0]["id"]

    dispatched = client.post("/api/v1/medication/dispatch-due", headers=family_headers)
    assert dispatched.status_code == 200
    assert dispatched.json()["dispatched"] == 1

    adherence = client.post(
        f"/api/v1/medication/reminders/{reminder_id}/adherence",
        json={"status": "taken", "notes": "Taken after breakfast"},
        headers=family_headers,
    )
    assert adherence.status_code == 200
    assert adherence.json()["status"] == "taken"

    summary = client.get("/api/v1/medication/adherence/u_parent", headers=family_headers)
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["taken"] == 1
    assert payload["adherence_rate"] == 1.0


def test_m08_adherence_endpoint_rejects_unknown_reminder():
    family_headers = _auth_headers("family@example.com", "Family@123")
    response = client.post(
        "/api/v1/medication/reminders/non-existent/adherence",
        json={"status": "missed"},
        headers=family_headers,
    )
    assert response.status_code == 404


def test_m08_metrics_include_adherence_record_count():
    family_headers = _auth_headers("family@example.com", "Family@123")

    schedule = client.post(
        "/api/v1/medication/schedules",
        json={
            "subject_user_id": "u_parent",
            "medication_name": "Aspirin",
            "dosage": "75mg",
            "reminder_message": "Take aspirin now",
        },
        headers=family_headers,
    )
    assert schedule.status_code == 200

    queued = client.post("/api/v1/medication/queue-due", headers=family_headers)
    reminder_id = queued.json()["items"][0]["id"]
    _ = client.post("/api/v1/medication/dispatch-due", headers=family_headers)

    _ = client.post(
        f"/api/v1/medication/reminders/{reminder_id}/adherence",
        json={"status": "skipped"},
        headers=family_headers,
    )

    metrics = client.get("/api/v1/medication/metrics", headers=family_headers)
    assert metrics.status_code == 200
    assert metrics.json()["adherence_records"] == 1
