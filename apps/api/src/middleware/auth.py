from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from src.modules.identity_access.models import Role

http_bearer = HTTPBearer(auto_error=False)


def _decode_access_token(token: str) -> dict:
    # Lazy import to avoid circular imports while keeping one auth source of truth.
    from src.interfaces.api.v1.auth import identity_service

    return identity_service.decode_access_token(token)


def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token is required")
    try:
        return _decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def require_role(*allowed_roles: Role) -> Callable[[dict], dict]:
    def dependency(claims: dict = Depends(require_auth)) -> dict:
        role = Role(claims["role"])
        if role not in set(allowed_roles):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return claims

    return dependency


class TokenValidatorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                request.state.claims = _decode_access_token(token)
            except JWTError:
                request.state.claims = None
        else:
            request.state.claims = None
        return await call_next(request)
