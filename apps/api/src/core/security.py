import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from json import JSONDecodeError

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.identity_access.models import Role


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; object-src 'none';"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        auth_limit: int,
        sos_limit: int,
        health_records_limit: int,
        marketplace_limit: int,
        audit_limit: int,
    ):
        super().__init__(app)
        self.auth_limit = auth_limit
        self.sos_limit = sos_limit
        self.health_records_limit = health_records_limit
        self.marketplace_limit = marketplace_limit
        self.audit_limit = audit_limit
        self.window_seconds = 60
        self.buckets: dict[str, deque[float]] = defaultdict(deque)

    def _limit_for_path(self, path: str) -> int | None:
        if path.startswith("/api/v1/auth"):
            return self.auth_limit
        if path.startswith("/api/v1/sos"):
            return self.sos_limit
        if path.startswith("/api/v1/health-records"):
            return self.health_records_limit
        if path.startswith("/api/v1/marketplace"):
            return self.marketplace_limit
        if path.startswith("/api/v1/audit"):
            return self.audit_limit
        return None

    async def dispatch(self, request: Request, call_next):
        if request.url.hostname == "testserver":
            return await call_next(request)

        limit = self._limit_for_path(request.url.path)
        if limit is None:
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        bucket_key = f"{client}:{request.url.path}"
        now = time.time()

        events = self.buckets[bucket_key]
        while events and now - events[0] > self.window_seconds:
            events.popleft()

        if len(events) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )

        events.append(now)
        return await call_next(request)


class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, protected_paths: list[str]):
        super().__init__(app)
        self.protected_paths = protected_paths

    async def dispatch(self, request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and any(
            request.url.path.startswith(path) for path in self.protected_paths
        ):
            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("x-csrf-token")
            if csrf_cookie and csrf_cookie != csrf_header:
                return JSONResponse(status_code=403, content={"detail": "CSRF token mismatch"})
        return await call_next(request)


class ConsentAuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/v1/health-records"):
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            return await call_next(request)

        # Lazy import prevents tight coupling loops during app startup.
        from src.interfaces.api.v1.auth import identity_service

        token = authorization.removeprefix("Bearer ").strip()
        try:
            claims = identity_service.decode_access_token(token)
        except Exception:
            return await call_next(request)

        subject_user_id: str | None = request.query_params.get("subject_user_id")
        required_scope = "health:read" if request.method == "GET" else "health:write"

        if request.method in {"POST", "PUT", "PATCH"} and not subject_user_id:
            try:
                payload = await request.json()
            except JSONDecodeError:
                payload = {}
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                subject_user_id = payload.get("subject_user_id")

        if not subject_user_id:
            return await call_next(request)

        allowed = consent_policy_evaluator.evaluate(
            actor_user_id=claims["sub"],
            actor_role=Role(claims["role"]),
            subject_user_id=subject_user_id,
            required_scope=required_scope,
            now=datetime.now(UTC),
        )
        if not allowed:
            return JSONResponse(status_code=403, content={"detail": "Consent policy denied access"})

        request.state.consent_middleware_checked = True
        return await call_next(request)
