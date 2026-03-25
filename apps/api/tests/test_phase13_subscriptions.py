from fastapi.testclient import TestClient

from src.interfaces.api.v1.auth import identity_service
from src.main import app
from src.modules.audit_logging.store import audit_log_store
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
    subscription_service.subscriptions.clear()
    subscription_service.invoices.clear()
    subscription_service.payment_events.clear()
    subscription_service.conversion_events.clear()
    audit_log_store.events.clear()
    audit_log_store.checkpoints.clear()
    audit_log_store.archives.clear()
    audit_log_store.anomalies.clear()


def test_plan_matrix_state_model_and_entitlements():
    family_headers = _auth_headers("family@example.com", "Family@123")

    matrix = client.get("/api/v1/subscriptions/matrix", headers=family_headers)
    assert matrix.status_code == 200
    assert "free" in matrix.json()["items"]
    assert "plus" in matrix.json()["items"]

    set_plan = client.post(
        "/api/v1/subscriptions/set-plan",
        json={"user_id": "u_family", "tenant_id": "tenant_a", "plan_code": PlanCode.plus.value, "start_trial": True},
        headers=family_headers,
    )
    assert set_plan.status_code == 200
    assert set_plan.json()["status"] in {"trialing", "active"}
    assert set_plan.json()["tenant_id"] == "tenant_a"

    entitlements = client.get("/api/v1/subscriptions/entitlements", headers=family_headers)
    assert entitlements.status_code == 200
    assert entitlements.json()["items"]["marketplace.booking"] is True

    check = client.get(
        "/api/v1/subscriptions/entitlements/check",
        params={"feature": "marketplace.booking"},
        headers=family_headers,
    )
    assert check.status_code == 200
    assert check.json()["enabled"] is True


def test_payment_provider_interface_lifecycle_and_ingestion_flow():
    family_headers = _auth_headers("family@example.com", "Family@123")

    set_plan = client.post(
        "/api/v1/subscriptions/set-plan",
        json={"user_id": "u_family", "plan_code": PlanCode.plus.value},
        headers=family_headers,
    )
    assert set_plan.status_code == 200

    checkout = client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan_code": PlanCode.plus.value, "provider": "demo"},
        headers=family_headers,
    )
    assert checkout.status_code == 200
    assert checkout.json()["provider"] == "demo"

    invoice = client.post(
        "/api/v1/subscriptions/invoices",
        json={"user_id": "u_family", "amount_cents": 7900, "provider": "demo", "currency": "USD"},
        headers=family_headers,
    )
    assert invoice.status_code == 200
    invoice_id = invoice.json()["id"]

    failed = client.post(
        "/api/v1/subscriptions/payments/events",
        json={
            "provider": "demo",
            "event_type": "payment.failed",
            "user_id": "u_family",
            "invoice_id": invoice_id,
            "amount_cents": 7900,
            "status": "failed",
        },
        headers=family_headers,
    )
    assert failed.status_code == 200

    grace = client.post("/api/v1/subscriptions/lifecycle/grace", json={"user_id": "u_family"}, headers=family_headers)
    assert grace.status_code == 200
    assert grace.json()["status"] == "grace_period"

    dunning = client.post("/api/v1/subscriptions/lifecycle/dunning", json={"user_id": "u_family"}, headers=family_headers)
    assert dunning.status_code == 200
    assert dunning.json()["dunning_attempts"] >= 1

    renew = client.post("/api/v1/subscriptions/lifecycle/renew", json={"user_id": "u_family"}, headers=family_headers)
    assert renew.status_code == 200
    assert renew.json()["status"] == "active"


def test_conversion_churn_audit_and_analytics_visibility():
    admin_headers = _auth_headers("admin@example.com", "Admin@123")
    family_headers = _auth_headers("family@example.com", "Family@123")

    upgrade = client.post(
        "/api/v1/subscriptions/set-plan",
        json={"user_id": "u_family", "plan_code": PlanCode.plus.value},
        headers=family_headers,
    )
    assert upgrade.status_code == 200

    cancel = client.post(
        "/api/v1/subscriptions/lifecycle/cancel",
        json={"user_id": "u_family"},
        headers=family_headers,
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    analytics = client.get("/api/v1/subscriptions/analytics", headers=admin_headers)
    assert analytics.status_code == 200
    assert analytics.json()["conversion_events"] >= 1
    assert analytics.json()["churn_events"] >= 1

    dashboard = client.get("/api/v1/admin-analytics/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["subscriptions"]["churn_events"] >= 1

    audit_events = client.get(
        "/api/v1/audit/events",
        params={"resource_type": "subscription"},
        headers=admin_headers,
    )
    assert audit_events.status_code == 200
    assert audit_events.json()["count"] >= 1
