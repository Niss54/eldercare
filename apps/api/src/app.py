from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.security import ConsentAuthorizationMiddleware, CSRFMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from src.di import get_container
from src.exceptions import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from src.health import router as health_router
from src.interfaces.api.v1.admin_analytics import router as admin_analytics_router
from src.interfaces.api.v1.audit import router as audit_router
from src.interfaces.api.v1.auth import router as auth_router
from src.interfaces.api.v1.consent import router as consent_router
from src.interfaces.api.v1.family_links import router as family_links_router
from src.interfaces.api.v1.health_records import router as health_records_router
from src.interfaces.api.v1.marketplace import router as marketplace_router
from src.interfaces.api.v1.medication import router as medication_router
from src.interfaces.api.v1.notifications import router as notifications_router
from src.interfaces.api.v1.realtime import router as realtime_router
from src.interfaces.api.v1.sos import router as sos_router
from src.interfaces.api.v1.subscriptions import router as subscriptions_router
from src.interfaces.api.v1.users import router as users_router
from src.interfaces.api.v2.placeholder import router as v2_placeholder_router
from src.interfaces.websocket.gateway import router as websocket_router
from src.logging_config import configure_logging
from src.metrics import MetricsMiddleware, router as metrics_router
from src.middleware.audit import AuditMiddleware
from src.middleware.auth import TokenValidatorMiddleware
from src.tracing import setup_tracing


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Lifespan hook is intentionally light in local mode; integrations initialize lazily.
    yield


def create_app() -> FastAPI:
    container = get_container()
    settings = container.settings
    configure_logging(settings.log_level)
    setup_tracing(settings)

    app = FastAPI(title="Eldercare API", version="0.1.0", lifespan=lifespan)

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.add_middleware(AuditMiddleware)
    app.add_middleware(TokenValidatorMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CSRFMiddleware,
        protected_paths=[path.strip() for path in settings.csrf_protected_paths.split(",") if path.strip()],
    )
    app.add_middleware(ConsentAuthorizationMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[host.strip() for host in settings.trusted_hosts.split(",") if host.strip()],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        RateLimitMiddleware,
        auth_limit=settings.auth_rate_limit_per_minute,
        sos_limit=settings.sos_rate_limit_per_minute,
        health_records_limit=settings.health_records_rate_limit_per_minute,
        marketplace_limit=settings.marketplace_rate_limit_per_minute,
        audit_limit=settings.audit_rate_limit_per_minute,
    )

    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(consent_router, prefix="/api/v1")
    app.include_router(family_links_router, prefix="/api/v1")
    app.include_router(health_records_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(admin_analytics_router, prefix="/api/v1")
    app.include_router(medication_router, prefix="/api/v1")
    app.include_router(marketplace_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(sos_router, prefix="/api/v1")
    app.include_router(subscriptions_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(realtime_router, prefix="/api/v1")
    app.include_router(v2_placeholder_router, prefix="/api/v2")
    app.include_router(websocket_router)

    return app
