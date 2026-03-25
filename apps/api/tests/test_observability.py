import json
import logging

from fastapi.testclient import TestClient

from src.app import create_app
from src.config import get_settings
from src.logging_config import JsonFormatter
from src.metrics import metrics_recorder
from src.tracing import setup_tracing


def setup_function():
    metrics_recorder.request_totals.clear()
    metrics_recorder.latencies_by_route.clear()
    metrics_recorder.errors_by_route.clear()
    metrics_recorder.medication_adherence_totals.clear()
    metrics_recorder.sos_response_time_seconds.clear()
    metrics_recorder.marketplace_conversion_totals.clear()
    metrics_recorder.websocket_active_connections.clear()
    metrics_recorder.websocket_disconnect_totals.clear()
    metrics_recorder.websocket_disconnect_timestamps.clear()


def test_json_formatter_contains_required_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello-observability",
        args=(),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))

    assert payload["message"] == "hello-observability"
    assert payload["level"] == "INFO"
    assert "timestamp" in payload
    assert "correlation_id" in payload


def test_metrics_endpoint_exposes_prometheus_format():
    app = create_app()
    client = TestClient(app)

    # Generate a few requests so metrics include real routes.
    client.get("/health")
    client.get("/ready")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    body = response.text
    assert "# HELP eldercare_http_requests_total" in body
    assert "eldercare_http_requests_total" in body
    assert "eldercare_http_request_latency_ms_p50" in body
    assert "eldercare_http_request_latency_ms_p95" in body
    assert "eldercare_http_request_latency_ms_p99" in body
    assert "eldercare_http_request_error_rate" in body
    assert "eldercare_medication_adherence_total" in body
    assert "eldercare_sos_response_time_seconds_p50" in body
    assert "eldercare_marketplace_conversion_total" in body
    assert "eldercare_websocket_connections_active" in body
    assert "eldercare_websocket_disconnect_total" in body
    assert "eldercare_websocket_disconnect_rate_per_min" in body
    assert 'path="/health"' in body


def test_domain_metrics_helpers_are_rendered():
    metrics_recorder.observe_medication_adherence("taken")
    metrics_recorder.observe_medication_adherence("missed")
    metrics_recorder.observe_sos_response_time(42.5)
    metrics_recorder.observe_sos_response_time(15.0)
    metrics_recorder.observe_marketplace_conversion("booking_requested")
    metrics_recorder.observe_websocket_connected("notifications")
    metrics_recorder.observe_websocket_disconnected("notifications", 1001)

    body = metrics_recorder.render_prometheus()
    assert 'eldercare_medication_adherence_total{status="taken"} 1' in body
    assert 'eldercare_medication_adherence_total{status="missed"} 1' in body
    assert "eldercare_sos_response_time_seconds_p50" in body
    assert 'eldercare_marketplace_conversion_total{stage="booking_requested"} 1' in body
    assert 'eldercare_websocket_connections_active{channel="notifications"} 0' in body
    assert 'eldercare_websocket_disconnect_total{channel="notifications",code="1001"} 1' in body


def test_tracing_setup_is_safe_when_otel_disabled_or_unavailable():
    settings = get_settings()
    enabled_before = settings.otel_enabled
    try:
        settings.otel_enabled = False
        assert setup_tracing(settings) is False

        settings.otel_enabled = True
        # Should not raise even when OpenTelemetry packages are unavailable.
        result = setup_tracing(settings)
        assert result in {True, False}
    finally:
        settings.otel_enabled = enabled_before
