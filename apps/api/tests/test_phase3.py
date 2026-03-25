from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.medication_reminders.service import medication_reminder_service
from src.modules.notifications.service import notification_service
from src.modules.realtime.service import realtime_service
from src.modules.sos_alerting.service import sos_service

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
    notification_service.deliveries.clear()
    sos_service.incidents.clear()
    realtime_service.events.clear()


def test_medication_reminders_dispatch_reliably_and_observable():
    family_headers = _auth_headers("family@example.com", "Family@123")

    create_schedule = client.post(
        "/api/v1/medication/schedules",
        json={
            "subject_user_id": "u_parent",
            "medication_name": "Aspirin",
            "dosage": "75mg",
            "reminder_message": "Take aspirin now",
        },
        headers=family_headers,
    )
    assert create_schedule.status_code == 200

    queued = client.post("/api/v1/medication/queue-due", headers=family_headers)
    assert queued.status_code == 200
    assert queued.json()["queued"] == 1

    first_dispatch = client.post("/api/v1/medication/dispatch-due", headers=family_headers)
    assert first_dispatch.status_code == 200
    assert first_dispatch.json()["dispatched"] == 1

    second_dispatch = client.post("/api/v1/medication/dispatch-due", headers=family_headers)
    assert second_dispatch.status_code == 200
    assert second_dispatch.json()["dispatched"] == 0

    metrics = client.get("/api/v1/medication/metrics", headers=family_headers)
    assert metrics.status_code == 200
    assert metrics.json()["reminders_dispatched"] == 1
    assert metrics.json()["dispatch_keys"] == 1

    notification_metrics = client.get("/api/v1/notifications/metrics", headers=family_headers)
    assert notification_metrics.status_code == 200
    assert notification_metrics.json()["delivered"] >= 1

    realtime_notifications = client.get("/api/v1/realtime/events/notifications", headers=family_headers)
    assert realtime_notifications.status_code == 200
    assert any(event["event_type"] == "notification.delivered" for event in realtime_notifications.json()["items"])


def test_sos_cascade_reaches_recipients_with_escalation_rules():
    family_headers = _auth_headers("family@example.com", "Family@123")
    doctor_headers = _auth_headers("doctor@example.com", "Doctor@123")
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    trigger = client.post(
        "/api/v1/sos/incidents/trigger",
        json={
            "subject_user_id": "u_parent",
            "severity": "critical",
            "cascade": [
                {"recipients": ["u_family"], "delay_seconds": 0},
                {"recipients": ["u_caregiver", "u_doctor"], "delay_seconds": 60},
            ],
        },
        headers=family_headers,
    )
    assert trigger.status_code == 200
    incident = trigger.json()
    assert incident["status"] == "escalated"
    assert len(incident["escalation_hops"]) == 2

    deliveries = client.get("/api/v1/notifications/deliveries", headers=admin_headers)
    assert deliveries.status_code == 200
    recipients = {item["recipient_user_id"] for item in deliveries.json()["items"]}
    assert {"u_family", "u_caregiver", "u_doctor"}.issubset(recipients)

    ack = client.post(f"/api/v1/sos/incidents/{incident['id']}/ack", headers=doctor_headers)
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"

    realtime_sos = client.get("/api/v1/realtime/events/sos", headers=family_headers)
    assert realtime_sos.status_code == 200
    event_types = {event["event_type"] for event in realtime_sos.json()["items"]}
    assert "sos.triggered" in event_types
    assert "sos.acknowledged" in event_types
