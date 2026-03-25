from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.notifications.service import (
    NotificationChannel,
    NotificationPriority,
    NotificationTemplate,
    notification_service,
)

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
    notification_service.deliveries.clear()
    notification_service.callbacks.clear()
    notification_service.preferences.clear()
    notification_service.throttle_history.clear()
    notification_service.dedup_history.clear()
    notification_service.templates = {
        "medication_due": NotificationTemplate(
            key="medication_due",
            channel=NotificationChannel.in_app,
            locale="en-US",
            priority=NotificationPriority.routine,
            body_template="Medication reminder: {message}",
        ),
        "sos_triggered": NotificationTemplate(
            key="sos_triggered",
            channel=NotificationChannel.sms,
            locale="en-US",
            priority=NotificationPriority.critical,
            body_template="SOS incident {incident_id} requires acknowledgement",
        ),
    }


def test_notification_event_contract_and_template_model():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    create_template = client.put(
        "/api/v1/notifications/templates/care_summary",
        json={
            "key": "care_summary",
            "channel": "email",
            "locale": "en-US",
            "priority": "routine",
            "body_template": "Daily summary for {name}: stable vitals",
        },
        headers=admin_headers,
    )
    assert create_template.status_code == 200

    send = client.post(
        "/api/v1/notifications/events/send",
        json={
            "event_type": "care.summary.ready",
            "recipient_user_id": "u_family",
            "template_key": "care_summary",
            "variables": {"name": "Maya"},
            "channels": ["email"],
            "priority": "routine",
        },
        headers=admin_headers,
    )
    assert send.status_code == 200
    item = send.json()["items"][0]
    assert item["channel"] == "email"
    assert "Maya" in item["message"]


def test_provider_abstraction_and_priority_tiers():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    send = client.post(
        "/api/v1/notifications/send",
        json={
            "recipient_user_id": "u_family",
            "message": "Critical care check",
            "channels": ["email", "sms", "push", "in_app"],
            "priority": "critical",
            "dedup_key": "provider-abstraction",
            "mode": "fanout",
        },
        headers=admin_headers,
    )
    assert send.status_code == 200
    items = send.json()["items"]
    assert len(items) == 4
    provider_names = {item["provider_name"] for item in items}
    assert "email-provider" in provider_names
    assert "sms-provider" in provider_names
    assert "push-provider" in provider_names
    assert "in-app-provider" in provider_names
    assert all(item["priority"] == "critical" for item in items)


def test_preferences_quiet_hours_and_critical_bypass():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")
    current_hour = datetime.now(UTC).hour

    pref = client.put(
        "/api/v1/notifications/preferences/u_family",
        json={
            "enabled_channels": ["in_app", "sms"],
            "quiet_hours_start_utc": current_hour,
            "quiet_hours_end_utc": (current_hour + 1) % 24,
            "locale": "en-US",
            "accessibility_plain_text": False,
        },
        headers=admin_headers,
    )
    assert pref.status_code == 200

    routine = client.post(
        "/api/v1/notifications/send",
        json={
            "recipient_user_id": "u_family",
            "message": "routine ping",
            "channels": ["in_app"],
            "priority": "routine",
            "dedup_key": "quiet-routine",
        },
        headers=admin_headers,
    )
    assert routine.status_code == 200
    assert routine.json()["items"][0]["status"] == "suppressed"

    critical = client.post(
        "/api/v1/notifications/send",
        json={
            "recipient_user_id": "u_family",
            "message": "critical ping",
            "channels": ["in_app"],
            "priority": "critical",
            "dedup_key": "quiet-critical",
        },
        headers=admin_headers,
    )
    assert critical.status_code == 200
    assert critical.json()["items"][0]["status"] == "delivered"


def test_delivery_tracking_callback_and_fallback():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    fallback = client.post(
        "/api/v1/notifications/send",
        json={
            "recipient_user_id": "u_family",
            "message": "__force_fail__ fallback test",
            "channels": ["sms", "in_app"],
            "priority": "urgent",
            "dedup_key": "fallback-test",
            "mode": "fallback",
        },
        headers=admin_headers,
    )
    assert fallback.status_code == 200
    items = fallback.json()["items"]
    assert len(items) == 2
    assert items[0]["channel"] == "sms"
    assert items[0]["status"] == "failed"
    assert items[1]["channel"] == "in_app"
    assert items[1]["status"] == "delivered"

    callback = client.post(
        "/api/v1/notifications/provider-callback",
        json={
            "delivery_id": items[1]["id"],
            "provider_name": items[1]["provider_name"],
            "external_status": "delivered",
            "payload": {"provider_event": "delivery_confirmed"},
        },
        headers=admin_headers,
    )
    assert callback.status_code == 200

    metrics = client.get("/api/v1/notifications/metrics", headers=admin_headers)
    assert metrics.status_code == 200
    assert metrics.json()["callbacks"] >= 1


def test_localization_accessibility_and_abuse_controls():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    pref = client.put(
        "/api/v1/notifications/preferences/u_family",
        json={
            "enabled_channels": ["in_app"],
            "locale": "hi-IN",
            "accessibility_plain_text": True,
        },
        headers=admin_headers,
    )
    assert pref.status_code == 200

    localized = client.post(
        "/api/v1/notifications/send",
        json={
            "recipient_user_id": "u_family",
            "message": "wellness check",
            "channels": ["in_app"],
            "priority": "routine",
            "dedup_key": "localized-accessible",
        },
        headers=admin_headers,
    )
    assert localized.status_code == 200
    assert localized.json()["items"][0]["message"].startswith("[HI] ACCESSIBLE NOTICE:")

    duplicate = client.post(
        "/api/v1/notifications/send",
        json={
            "recipient_user_id": "u_family",
            "message": "wellness check",
            "channels": ["in_app"],
            "priority": "routine",
            "dedup_key": "localized-accessible",
        },
        headers=admin_headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["items"][0]["provider_name"] == "dedup-guard"

    suppressed = client.post(
        "/api/v1/notifications/send",
        json={
            "recipient_user_id": "u_family",
            "message": "spam broadcast",
            "channels": ["in_app"],
            "priority": "routine",
            "dedup_key": "suppression-rule",
        },
        headers=admin_headers,
    )
    assert suppressed.status_code == 200
    assert suppressed.json()["items"][0]["provider_name"] == "suppression-rule"

    for i in range(25):
        _ = client.post(
            "/api/v1/notifications/send",
            json={
                "recipient_user_id": "u_family",
                "message": f"burst-{i}",
                "channels": ["in_app"],
                "priority": "routine",
                "dedup_key": f"burst-{i}",
            },
            headers=admin_headers,
        )

    deliveries = client.get("/api/v1/notifications/deliveries", headers=admin_headers)
    assert deliveries.status_code == 200
    assert any(item["provider_name"] == "throttle" for item in deliveries.json()["items"])
