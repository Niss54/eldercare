from fastapi.testclient import TestClient

from src.app import create_app
from src.config import get_settings
from src.di import get_container


def test_app_bootstrap_and_health_endpoints():
    app = create_app()
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_di_container_resolves_settings_singleton():
    container = get_container()
    settings = get_settings()
    assert container.settings is settings
    assert settings.api_port > 0
