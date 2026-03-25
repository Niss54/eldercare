from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.notifications.application.services import notification_service_m07
from src.modules.notifications.infrastructure.providers.email import EmailProvider
from src.modules.notifications.infrastructure.providers.sms import SmsProvider
from src.modules.notifications.service import notification_service
from src.workers.notification_tasks import send_email, send_sms

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


def test_m07_application_send_supports_template_rendering():
    result = notification_service_m07.send(
        recipient_id="u_family",
        type="care.summary",
        data={
            "template_key": "medication_due",
            "variables": {"message": "Take insulin"},
            "channels": ["in_app"],
            "priority": "routine",
            "dedup_key": "m07-template-test",
            "mode": "fanout",
        },
    )
    assert result.recipient_id == "u_family"
    assert result.status.value in {"sent", "delivered"}

    deliveries = notification_service.list_deliveries(recipient_user_id="u_family")
    assert len(deliveries) >= 1
    assert "Take insulin" in deliveries[-1].message


def test_m07_provider_failure_path_and_stub_behavior():
    sms_provider = SmsProvider()
    ok = sms_provider.send("u_family", "hello")
    assert ok.success is True

    failed = sms_provider.send("u_family", "__force_fail__ simulate")
    assert failed.success is False
    assert failed.error_message is not None



def test_m07_email_provider_dry_run_returns_success():
    provider = EmailProvider(dry_run=True)
    result = provider.send("family@example.com", "Care update", {"subject": "Daily Care"})
    assert result.success is True
    assert result.provider_name == "email-smtp"
    assert result.provider_message_id is not None



def test_m07_api_send_and_preferences_endpoints():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")

    pref = client.put(
        "/api/v1/notifications/preferences/u_family",
        json={
            "enabled_channels": ["email", "sms"],
            "quiet_hours_start_utc": 22,
            "quiet_hours_end_utc": 6,
            "locale": "en-US",
            "accessibility_plain_text": False,
        },
        headers=admin_headers,
    )
    assert pref.status_code == 200
    assert pref.json()["user_id"] == "u_family"

    sent = client.post(
        "/api/v1/notifications/send",
        json={
            "recipient_user_id": "u_family",
            "message": "Care summary ready",
            "channels": ["email"],
            "priority": "routine",
            "dedup_key": "m07-api-send",
            "mode": "fanout",
        },
        headers=admin_headers,
    )
    assert sent.status_code == 200
    assert sent.json()["count"] >= 1



def test_m07_worker_tasks_execute_without_celery_runtime():
    email_result = send_email(
        recipient_id="u_family",
        type="worker.email",
        data={
            "message": "Worker email notice",
            "channels": ["email"],
            "priority": "routine",
            "dedup_key": "worker-email",
        },
    )
    assert email_result["recipient_id"] == "u_family"

    sms_result = send_sms(
        recipient_id="u_family",
        type="worker.sms",
        data={
            "message": "Worker sms notice",
            "channels": ["sms"],
            "priority": "routine",
            "dedup_key": "worker-sms",
        },
    )
    assert sms_result["recipient_id"] == "u_family"
