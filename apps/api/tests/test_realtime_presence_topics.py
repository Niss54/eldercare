from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import DEMO_USERS, identity_service
from src.main import app
from src.modules.identity_access.service import hash_password
from src.modules.realtime.service import realtime_service

client = TestClient(app)


def _reset_demo_passwords() -> None:
    DEMO_USERS["admin@example.com"].password_hash = hash_password("Admin@123")
    DEMO_USERS["family@example.com"].password_hash = hash_password("Family@123")
    DEMO_USERS["parent@example.com"].password_hash = hash_password("Parent@123")
    DEMO_USERS["caregiver@example.com"].password_hash = hash_password("Caregiver@123")
    DEMO_USERS["doctor@example.com"].password_hash = hash_password("Doctor@123")


def setup_function() -> None:
    identity_service.sessions.clear()
    identity_service.revoked_refresh_jtis.clear()
    realtime_service.reset()
    _reset_demo_passwords()


def _login(email: str, password: str) -> dict:
    payload = {"email": email, "password": password}
    if email in {"admin@example.com", "doctor@example.com"}:
        challenge = client.post("/api/v1/auth/mfa/challenge", json={"username": email})
        assert challenge.status_code == 200
        ticket = challenge.json()
        payload["mfa_ticket"] = ticket["ticket"]
        payload["mfa_code"] = ticket["otp_dev_only"]

    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    return response.json()


def test_notifications_presence_tracks_multiple_connections():
    family = _login("family@example.com", "Family@123")
    doctor = _login("doctor@example.com", "Doctor@123")

    family_headers = {"Authorization": f"Bearer {family['access_token']}"}

    with client.websocket_connect(f"/ws/notifications?token={family['access_token']}") as ws_family:
        connected_family = ws_family.receive_json()
        assert connected_family["event_type"] == "ws.connected"

        with client.websocket_connect(f"/ws/notifications?token={doctor['access_token']}") as ws_doctor:
            connected_doctor = ws_doctor.receive_json()
            assert connected_doctor["event_type"] == "ws.connected"

            snapshot = client.get("/api/v1/realtime/presence/notifications", headers=family_headers)
            assert snapshot.status_code == 200
            payload = snapshot.json()
            assert payload["online_users"] == 2
            assert payload["active_connections"] == 2

            ws_doctor.send_json({"action": "ping"})
            pong = ws_doctor.receive_json()
            assert pong["event_type"] == "ws.pong"
            assert pong["presence"]["online_users"] == 2

    after = client.get("/api/v1/realtime/presence/notifications", headers=family_headers)
    assert after.status_code == 200
    assert after.json()["online_users"] == 0


def test_topic_subscription_and_event_query_by_topic():
    doctor = _login("doctor@example.com", "Doctor@123")
    headers = {"Authorization": f"Bearer {doctor['access_token']}"}

    with client.websocket_connect(f"/ws/sos/incident-77?token={doctor['access_token']}") as ws:
        connected = ws.receive_json()
        assert connected["event_type"] == "ws.connected"
        assert connected["topic"] == "incident-77"

        ws.send_json({"action": "subscribe", "topic": "incident-88"})
        subscribed = ws.receive_json()
        assert subscribed["event_type"] == "ws.subscribed"
        assert "incident-88" in subscribed["subscriptions"]

        ws.send_json(
            {
                "action": "publish",
                "event_type": "sos.custom.update",
                "topic": "incident-88",
                "payload": {"status": "escalated"},
            }
        )
        event = ws.receive_json()
        assert event["event_type"] == "sos.custom.update"
        assert event["topic"] == "incident-88"

    subs = client.get("/api/v1/realtime/subscriptions/sos", headers=headers)
    assert subs.status_code == 200
    assert isinstance(subs.json().get("topics"), dict)

    topic_events = client.get("/api/v1/realtime/events/sos?topic=incident-88", headers=headers)
    assert topic_events.status_code == 200
    assert topic_events.json()["count"] >= 1
    assert all(item["topic"] == "incident-88" for item in topic_events.json()["items"])
