from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.audit_logging.store import audit_log_store
from src.modules.notifications.service import notification_service
from src.modules.realtime.service import realtime_service
from src.modules.sos_alerting.service import IncidentStatus, sos_service

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
    sos_service.incidents.clear()
    audit_log_store.events.clear()
    audit_log_store.checkpoints.clear()
    audit_log_store.archives.clear()
    audit_log_store.anomalies.clear()
    realtime_service.events.clear()


def test_sos_state_machine_and_resolve_flow():
    family_headers = _auth_headers("family@example.com", "Family@123")
    doctor_headers = _auth_headers("doctor@example.com", "Doctor@123")

    trigger = client.post(
        "/api/v1/sos/incidents/trigger",
        json={
            "subject_user_id": "u_parent",
            "severity": "critical",
            "cascade": [
                {"target_roles": ["caregiver"], "delay_seconds": 0},
                {"target_roles": ["doctor"], "delay_seconds": 60},
            ],
        },
        headers=family_headers,
    )
    assert trigger.status_code == 200
    incident_id = trigger.json()["id"]
    assert trigger.json()["status"] == IncidentStatus.escalated.value

    ack = client.post(f"/api/v1/sos/incidents/{incident_id}/ack", headers=doctor_headers)
    assert ack.status_code == 200
    assert ack.json()["status"] == IncidentStatus.acknowledged.value

    resolve = client.post(f"/api/v1/sos/incidents/{incident_id}/resolve", json={}, headers=doctor_headers)
    assert resolve.status_code == 200
    assert resolve.json()["status"] == IncidentStatus.resolved.value


def test_cascade_policy_graph_and_first_responder_selection():
    family_headers = _auth_headers("family@example.com", "Family@123")

    trigger = client.post(
        "/api/v1/sos/incidents/trigger",
        json={
            "subject_user_id": "u_parent",
            "severity": "critical",
            "cascade": [
                {
                    "target_roles": ["caregiver", "doctor"],
                    "delay_seconds": 0,
                    "fallback_roles": ["admin"],
                }
            ],
        },
        headers=family_headers,
    )
    assert trigger.status_code == 200
    hop = trigger.json()["escalation_hops"][0]
    assert "caregiver" in hop["target_roles"]
    assert "doctor" in hop["target_roles"]
    assert len(hop["recipients"]) >= 1


def test_escalation_retries_parallel_channels_and_fallback_if_unacked():
    family_headers = _auth_headers("family@example.com", "Family@123")

    incident = sos_service.trigger_incident(
        subject_user_id="u_parent",
        initiated_by_user_id="u_family",
        severity="critical",
        cascade=[
            {
                "target_roles": ["caregiver"],
                "delay_seconds": 0,
                "max_retries": 1,
                "retry_delay_seconds": 1,
                "fallback_recipients": ["u_admin"],
            }
        ],
    )

    # Force retry and fallback progression.
    _ = sos_service.process_escalation_tick(
        incident_id=incident.id,
        now=datetime.now(UTC) + timedelta(seconds=5),
        network_outage=False,
    )
    _ = sos_service.process_escalation_tick(
        incident_id=incident.id,
        now=datetime.now(UTC) + timedelta(seconds=15),
        network_outage=False,
    )

    timeline = client.get(f"/api/v1/sos/incidents/{incident.id}/timeline", headers=family_headers)
    assert timeline.status_code == 200
    event_types = {item["event_type"] for item in timeline.json()["items"]}
    assert "incident.escalation_retry" in event_types
    assert "incident.fallback_invoked" in event_types

    # Parallel channel expectation: critical dispatch includes sms + push + in_app.
    channels = {d.channel.value for d in notification_service.deliveries if d.event_id.startswith("manual") or "sos" in d.message.lower()}
    assert "sms" in channels
    assert "push" in channels
    assert "in_app" in channels


def test_realtime_updates_and_audit_forensic_timeline_capture():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")
    family_headers = _auth_headers("family@example.com", "Family@123")

    trigger = client.post(
        "/api/v1/sos/incidents/trigger",
        json={"subject_user_id": "u_parent", "severity": "critical", "cascade": [{"recipients": ["u_family"], "delay_seconds": 0}]},
        headers=family_headers,
    )
    assert trigger.status_code == 200
    incident_id = trigger.json()["id"]

    process = client.post(
        f"/api/v1/sos/incidents/{incident_id}/process-escalation",
        json={"network_outage": False},
        headers=family_headers,
    )
    assert process.status_code == 200

    realtime = client.get("/api/v1/realtime/events/sos", headers=family_headers)
    assert realtime.status_code == 200
    rt_types = {event["event_type"] for event in realtime.json()["items"]}
    assert "sos.triggered" in rt_types
    assert "sos.escalation_updated" in rt_types

    audit = client.get("/api/v1/audit/events", headers=admin_headers)
    assert audit.status_code == 200
    assert any(item["resource_type"] == "sos_incident" for item in audit.json()["items"])

    timeline = client.get(f"/api/v1/sos/incidents/{incident_id}/timeline", headers=family_headers)
    assert timeline.status_code == 200
    assert timeline.json()["count"] >= 2


def test_simulation_suite_day_night_and_network_outage():
    doctor_headers = _auth_headers("doctor@example.com", "Doctor@123")

    day = client.post("/api/v1/sos/simulations/run", json={"scenario": "day"}, headers=doctor_headers)
    assert day.status_code == 200
    assert day.json()["scenario"] == "day"
    assert day.json()["timeline_events"] >= 2

    night = client.post("/api/v1/sos/simulations/run", json={"scenario": "night"}, headers=doctor_headers)
    assert night.status_code == 200
    assert night.json()["scenario"] == "night"
    assert night.json()["total_retries"] >= 1

    outage = client.post("/api/v1/sos/simulations/run", json={"scenario": "network_outage"}, headers=doctor_headers)
    assert outage.status_code == 200
    assert outage.json()["scenario"] == "network_outage"
    assert outage.json()["timeline_events"] >= 2
