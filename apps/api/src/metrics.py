from __future__ import annotations

import statistics
import time
from collections import defaultdict, deque

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

MAX_SAMPLES_PER_ROUTE = 512


class MetricsRecorder:
    def __init__(self) -> None:
        self.request_totals: dict[tuple[str, str, str], int] = defaultdict(int)
        self.latencies_by_route: dict[tuple[str, str], deque[float]] = defaultdict(
            lambda: deque(maxlen=MAX_SAMPLES_PER_ROUTE),
        )
        self.errors_by_route: dict[tuple[str, str], int] = defaultdict(int)
        self.medication_adherence_totals: dict[str, int] = defaultdict(int)
        self.sos_response_time_seconds: deque[float] = deque(maxlen=MAX_SAMPLES_PER_ROUTE)
        self.marketplace_conversion_totals: dict[str, int] = defaultdict(int)
        self.websocket_active_connections: dict[str, int] = defaultdict(int)
        self.websocket_disconnect_totals: dict[tuple[str, str], int] = defaultdict(int)
        self.websocket_disconnect_timestamps: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=MAX_SAMPLES_PER_ROUTE),
        )

    def observe(self, method: str, path: str, status_code: int, latency_ms: float) -> None:
        status_class = f"{status_code // 100}xx"
        self.request_totals[(method, path, status_class)] += 1
        key = (method, path)
        self.latencies_by_route[key].append(latency_ms)
        if status_code >= 500:
            self.errors_by_route[key] += 1

    def observe_medication_adherence(self, status: str) -> None:
        self.medication_adherence_totals[status] += 1

    def observe_sos_response_time(self, seconds: float) -> None:
        self.sos_response_time_seconds.append(max(0.0, seconds))

    def observe_marketplace_conversion(self, stage: str) -> None:
        self.marketplace_conversion_totals[stage] += 1

    def observe_websocket_connected(self, channel: str) -> None:
        self.websocket_active_connections[channel] += 1

    def observe_websocket_disconnected(self, channel: str, code: int | None) -> None:
        safe_code = str(code if code is not None else 1000)
        self.websocket_disconnect_totals[(channel, safe_code)] += 1
        self.websocket_disconnect_timestamps[channel].append(time.time())
        self.websocket_active_connections[channel] = max(0, self.websocket_active_connections[channel] - 1)

    def _percentile(self, samples: list[float], quantile: float) -> float:
        if not samples:
            return 0.0
        if len(samples) == 1:
            return samples[0]
        index = int(round((len(samples) - 1) * quantile))
        return sorted(samples)[index]

    def render_prometheus(self) -> str:
        lines: list[str] = []

        lines.append("# HELP eldercare_http_requests_total Total HTTP requests by method, path and status class")
        lines.append("# TYPE eldercare_http_requests_total counter")
        for (method, path, status_class), count in sorted(self.request_totals.items()):
            lines.append(
                f'eldercare_http_requests_total{{method="{method}",path="{path}",status_class="{status_class}"}} {count}',
            )

        lines.append("# HELP eldercare_http_request_latency_ms_p50 P50 request latency in milliseconds")
        lines.append("# TYPE eldercare_http_request_latency_ms_p50 gauge")
        lines.append("# HELP eldercare_http_request_latency_ms_p95 P95 request latency in milliseconds")
        lines.append("# TYPE eldercare_http_request_latency_ms_p95 gauge")
        lines.append("# HELP eldercare_http_request_latency_ms_p99 P99 request latency in milliseconds")
        lines.append("# TYPE eldercare_http_request_latency_ms_p99 gauge")

        lines.append("# HELP eldercare_http_request_error_rate Error rate per route (5xx/total)")
        lines.append("# TYPE eldercare_http_request_error_rate gauge")

        for (method, path), values in sorted(self.latencies_by_route.items()):
            samples = list(values)
            p50 = self._percentile(samples, 0.50)
            p95 = self._percentile(samples, 0.95)
            p99 = self._percentile(samples, 0.99)
            total = sum(
                count
                for (m, p, _), count in self.request_totals.items()
                if m == method and p == path
            )
            errors = self.errors_by_route.get((method, path), 0)
            error_rate = (errors / total) if total else 0.0

            lines.append(f'eldercare_http_request_latency_ms_p50{{method="{method}",path="{path}"}} {p50:.2f}')
            lines.append(f'eldercare_http_request_latency_ms_p95{{method="{method}",path="{path}"}} {p95:.2f}')
            lines.append(f'eldercare_http_request_latency_ms_p99{{method="{method}",path="{path}"}} {p99:.2f}')
            lines.append(f'eldercare_http_request_error_rate{{method="{method}",path="{path}"}} {error_rate:.6f}')

        if not self.request_totals:
            # Keep metric families visible even on empty traffic.
            lines.append('eldercare_http_requests_total{method="none",path="none",status_class="0xx"} 0')
            lines.append('eldercare_http_request_latency_ms_p50{method="none",path="none"} 0')
            lines.append('eldercare_http_request_latency_ms_p95{method="none",path="none"} 0')
            lines.append('eldercare_http_request_latency_ms_p99{method="none",path="none"} 0')
            lines.append('eldercare_http_request_error_rate{method="none",path="none"} 0')

        lines.append("# HELP eldercare_medication_adherence_total Total medication adherence events by status")
        lines.append("# TYPE eldercare_medication_adherence_total counter")
        for status_key, count in sorted(self.medication_adherence_totals.items()):
            lines.append(f'eldercare_medication_adherence_total{{status="{status_key}"}} {count}')
        if not self.medication_adherence_totals:
            lines.append('eldercare_medication_adherence_total{status="none"} 0')

        lines.append("# HELP eldercare_sos_response_time_seconds_p50 P50 SOS response time in seconds")
        lines.append("# TYPE eldercare_sos_response_time_seconds_p50 gauge")
        lines.append("# HELP eldercare_sos_response_time_seconds_p95 P95 SOS response time in seconds")
        lines.append("# TYPE eldercare_sos_response_time_seconds_p95 gauge")
        sos_samples = list(self.sos_response_time_seconds)
        sos_p50 = self._percentile(sos_samples, 0.50)
        sos_p95 = self._percentile(sos_samples, 0.95)
        lines.append(f"eldercare_sos_response_time_seconds_p50 {sos_p50:.3f}")
        lines.append(f"eldercare_sos_response_time_seconds_p95 {sos_p95:.3f}")

        lines.append("# HELP eldercare_marketplace_conversion_total Marketplace conversion events by stage")
        lines.append("# TYPE eldercare_marketplace_conversion_total counter")
        for stage, count in sorted(self.marketplace_conversion_totals.items()):
            lines.append(f'eldercare_marketplace_conversion_total{{stage="{stage}"}} {count}')
        if not self.marketplace_conversion_totals:
            lines.append('eldercare_marketplace_conversion_total{stage="none"} 0')

        lines.append("# HELP eldercare_websocket_connections_active Active websocket connections by channel")
        lines.append("# TYPE eldercare_websocket_connections_active gauge")
        for channel, count in sorted(self.websocket_active_connections.items()):
            lines.append(f'eldercare_websocket_connections_active{{channel="{channel}"}} {count}')
        if not self.websocket_active_connections:
            lines.append('eldercare_websocket_connections_active{channel="none"} 0')

        lines.append("# HELP eldercare_websocket_disconnect_total Total websocket disconnects by channel and close code")
        lines.append("# TYPE eldercare_websocket_disconnect_total counter")
        for (channel, code), count in sorted(self.websocket_disconnect_totals.items()):
            lines.append(f'eldercare_websocket_disconnect_total{{channel="{channel}",code="{code}"}} {count}')
        if not self.websocket_disconnect_totals:
            lines.append('eldercare_websocket_disconnect_total{channel="none",code="0"} 0')

        lines.append("# HELP eldercare_websocket_disconnect_rate_per_min Websocket disconnects per minute by channel")
        lines.append("# TYPE eldercare_websocket_disconnect_rate_per_min gauge")
        now = time.time()
        for channel, timestamps in sorted(self.websocket_disconnect_timestamps.items()):
            recent = [ts for ts in timestamps if now - ts <= 60]
            lines.append(f'eldercare_websocket_disconnect_rate_per_min{{channel="{channel}"}} {float(len(recent)):.2f}')
        if not self.websocket_disconnect_timestamps:
            lines.append('eldercare_websocket_disconnect_rate_per_min{channel="none"} 0')

        return "\n".join(lines) + "\n"


metrics_recorder = MetricsRecorder()
router = APIRouter(tags=["observability"])


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        metrics_recorder.observe(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        return response


@router.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return metrics_recorder.render_prometheus()
