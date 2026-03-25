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


def test_websocket_presence_tracking_for_dashboard():
    family_login = _login("family@example.com", "Family@123")
    token = family_login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    before = client.get("/api/v1/realtime/presence/notifications", headers=headers)
    assert before.status_code == 200
    assert before.json()["online_users"] == 0

    with client.websocket_connect(f"/ws/notifications?token={token}") as ws:
        connected = ws.receive_json()
        assert connected["event_type"] == "ws.connected"
        assert connected["channel"] == "notifications"
        assert connected["user_id"] == "u_family"

        ws.send_json({"action": "ping"})
        pong = ws.receive_json()
        assert pong["event_type"] == "ws.pong"
        assert pong["presence"]["online_users"] == 1

        during = client.get("/api/v1/realtime/presence/notifications", headers=headers)
        assert during.status_code == 200
        assert during.json()["online_users"] == 1
        assert during.json()["active_connections"] == 1
        assert during.json()["users"][0]["user_id"] == "u_family"

    after = client.get("/api/v1/realtime/presence/notifications", headers=headers)
    assert after.status_code == 200
    assert after.json()["online_users"] == 0


def test_topic_based_routing_and_subscription_management():
    doctor_login = _login("doctor@example.com", "Doctor@123")
    token = doctor_login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with client.websocket_connect(f"/ws/sos/incident-1?token={token}") as ws:
        connected = ws.receive_json()
        assert connected["event_type"] == "ws.connected"
        assert connected["channel"] == "sos"
        assert connected["topic"] == "incident-1"

        snapshot = client.get("/api/v1/realtime/subscriptions/sos", headers=headers)
        assert snapshot.status_code == 200
        assert snapshot.json()["topics"].get("incident-1") == 1

        ws.send_json({"action": "subscribe", "topic": "incident-2"})
        subscribed = ws.receive_json()
        assert subscribed["event_type"] == "ws.subscribed"
        assert "incident-2" in subscribed["subscriptions"]

        snapshot_two = client.get("/api/v1/realtime/subscriptions/sos", headers=headers)
        assert snapshot_two.status_code == 200
        assert snapshot_two.json()["topics"].get("incident-1") == 1
        assert snapshot_two.json()["topics"].get("incident-2") == 1

        ws.send_json(
            {
                "action": "publish",
                "event_type": "sos.custom",
                "topic": "incident-2",
                "payload": {"state": "updated"},
            }
        )
        routed = ws.receive_json()
        assert routed["event_type"] == "sos.custom"
        assert routed["topic"] == "incident-2"

        ws.send_json({"action": "unsubscribe", "topic": "incident-1"})
        unsubscribed = ws.receive_json()
        assert unsubscribed["event_type"] == "ws.unsubscribed"

    events = client.get("/api/v1/realtime/events/sos?topic=incident-2", headers=headers)
    assert events.status_code == 200
    assert events.json()["count"] >= 1
    assert all(item["topic"] == "incident-2" for item in events.json()["items"])
