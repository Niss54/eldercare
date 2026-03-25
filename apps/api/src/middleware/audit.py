import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.modules.audit_logging.store import AuditOutcome, AuditSeverity, RequestContext, audit_log_store

logger = logging.getLogger("eldercare.api")

_SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "secret",
    "otp",
    "mfa_code",
    "mfa_ticket",
}


def _domain_from_path(path: str) -> str:
    if not path.startswith("/api/"):
        return "platform"
    parts = [part for part in path.split("/") if part]
    if len(parts) < 3:
        return "platform"
    return parts[2].replace("-", "_")


def _mask_value(key: str, value: str) -> str:
    if key.lower() in _SENSITIVE_KEYS:
        return "***"
    return value[:128]


def _masked_query(request: Request) -> dict[str, str]:
    items: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        items[key] = _mask_value(key, value)
    return items


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        actor_user_id = "anonymous"
        actor_role = None
        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
            try:
                from src.interfaces.api.v1.auth import identity_service

                claims = identity_service.decode_access_token(token)
                actor_user_id = claims.get("sub", "anonymous")
                actor_role = claims.get("role")
            except Exception:
                actor_user_id = "invalid_token"

        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id

        status_code = response.status_code
        if status_code >= 500:
            outcome = AuditOutcome.failure
            severity = AuditSeverity.critical
        elif status_code in {401, 403, 429}:
            outcome = AuditOutcome.denied
            severity = AuditSeverity.warning
        else:
            outcome = AuditOutcome.success
            severity = AuditSeverity.info

        request_context = RequestContext(
            method=request.method,
            path=request.url.path,
            query_keys=sorted(list(request.query_params.keys())),
            status_code=status_code,
            ip_hash=audit_log_store._hash_ip(request.client.host if request.client else None),
            user_agent=(request.headers.get("user-agent") or "")[:120] or None,
        )
        audit_log_store.publish_domain_event(
            domain=_domain_from_path(request.url.path),
            action=f"http.{request.method.lower()}",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            resource_id=request.url.path,
            correlation_id=correlation_id,
            request=request_context,
            outcome=outcome,
            severity=severity,
            metadata={
                "content_type": (request.headers.get("content-type") or "")[:80],
                "response_content_type": (response.headers.get("content-type") or "")[:80],
                "query": str(_masked_query(request))[:400],
            },
        )

        logger.info(
            "audit_event",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": status_code,
                "correlation_id": correlation_id,
            },
        )
        return response
