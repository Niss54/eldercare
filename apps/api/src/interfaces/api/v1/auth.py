import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel, ConfigDict

from src.core.settings import Settings, get_settings
from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.identity_access.models import ROLE_PERMISSIONS, Role, User, role_permissions
from src.modules.identity_access.service import IdentityService, hash_password

router = APIRouter(prefix="/auth", tags=["auth"])
http_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = None
    email: str | None = None
    password: str
    mfa_ticket: str | None = None
    mfa_code: str | None = None


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str | None = None
    refresh_token: str | None = None


class MfaChallengeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    purpose: str = "login"


class MfaVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket: str
    code: str


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    reset_token: str
    new_password: str


DEMO_USERS: dict[str, User] = {
    "admin@example.com": User(
        id="u_admin",
        username="admin@example.com",
        full_name="Platform Admin",
        role=Role.admin,
        password_hash=hash_password("Admin@123"),
    ),
    "family@example.com": User(
        id="u_family",
        username="family@example.com",
        full_name="Family Member",
        role=Role.family_member,
        password_hash=hash_password("Family@123"),
    ),
    "parent@example.com": User(
        id="u_parent",
        username="parent@example.com",
        full_name="Parent User",
        role=Role.parent,
        password_hash=hash_password("Parent@123"),
    ),
    "caregiver@example.com": User(
        id="u_caregiver",
        username="caregiver@example.com",
        full_name="Caregiver User",
        role=Role.caregiver,
        password_hash=hash_password("Caregiver@123"),
    ),
    "doctor@example.com": User(
        id="u_doctor",
        username="doctor@example.com",
        full_name="Doctor User",
        role=Role.doctor,
        password_hash=hash_password("Doctor@123"),
    ),
}

identity_service = IdentityService(settings=get_settings(), users=DEMO_USERS)
MFA_TICKETS: dict[str, dict] = {}
MFA_REQUIRED_ROLES: set[Role] = {Role.admin, Role.doctor}


def _validate_mfa(ticket: str, code: str) -> dict:
    ticket_data = MFA_TICKETS.get(ticket)
    if not ticket_data:
        raise HTTPException(status_code=401, detail="Invalid MFA ticket")
    if datetime.now(UTC) > ticket_data["expires_at"]:
        raise HTTPException(status_code=401, detail="MFA ticket expired")
    if code != ticket_data["code"]:
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    return ticket_data


def _get_claims(credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token is required")
    try:
        return identity_service.decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def _require_permission(permission: str):
    def dependency(claims: dict = Depends(_get_claims)) -> dict:
        claim_permissions = set(claims.get("permissions", []))
        if permission not in claim_permissions:
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return claims

    return dependency


@router.get("/roles")
def list_roles() -> dict[str, list[str]]:
    return {"roles": [role.value for role in Role]}


@router.get("/permissions")
def list_role_permissions() -> dict[str, list[str]]:
    return {role.value: sorted(permissions) for role, permissions in ROLE_PERMISSIONS.items()}


@router.post("/login")
def login(payload: LoginRequest):
    username = payload.username or payload.email
    if not username:
        raise HTTPException(status_code=422, detail="username or email is required")
    user = identity_service.authenticate(username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if user.role in MFA_REQUIRED_ROLES:
        if not payload.mfa_ticket or not payload.mfa_code:
            raise HTTPException(status_code=401, detail="MFA required for this role")
        ticket_data = _validate_mfa(payload.mfa_ticket, payload.mfa_code)
        if ticket_data["username"] != user.username:
            raise HTTPException(status_code=401, detail="MFA ticket user mismatch")
        del MFA_TICKETS[payload.mfa_ticket]

    token_pair = identity_service.issue_token_pair(user)
    return {
        **token_pair,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value,
        },
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    if payload.reset_token != "dev-reset-token":
        raise HTTPException(status_code=401, detail="Invalid reset token")

    user = DEMO_USERS.get(payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user.password_hash = hash_password(payload.new_password)
    return {"status": "password_reset", "username": user.username}


@router.post("/refresh")
def refresh(payload: RefreshRequest):
    try:
        _, token_pair = identity_service.rotate_refresh_token(payload.refresh_token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    return token_pair


@router.post("/mfa/challenge")
def mfa_challenge(payload: MfaChallengeRequest):
    user = DEMO_USERS.get(payload.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ticket = secrets.token_urlsafe(12)
    code = f"{secrets.randbelow(1000000):06d}"
    MFA_TICKETS[ticket] = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value,
        "code": code,
        "expires_at": datetime.now(UTC) + timedelta(minutes=5),
    }
    # The demo OTP is returned explicitly for local development and tests.
    return {"ticket": ticket, "expires_in": 300, "otp_dev_only": code}


@router.post("/mfa/verify")
def mfa_verify(payload: MfaVerifyRequest):
    ticket_data = _validate_mfa(payload.ticket, payload.code)

    user = DEMO_USERS[ticket_data["username"]]
    token_pair = identity_service.issue_token_pair(user)
    del MFA_TICKETS[payload.ticket]
    return {
        **token_pair,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value,
        },
    }


@router.post("/logout")
def logout(payload: LogoutRequest, claims: dict = Depends(_get_claims)):
    session_id = payload.session_id or claims.get("sid")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    identity_service.revoke_session(session_id)
    if payload.refresh_token:
        try:
            identity_service.revoke_refresh_token(payload.refresh_token)
        except JWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    return {"status": "logged_out", "session_id": session_id}


@router.get("/whoami")
def whoami(
    x_role: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    if not x_role:
        raise HTTPException(status_code=401, detail="x-role header is required")
    return {
        "role": x_role,
        "environment": settings.app_env,
        "server_time": datetime.now(UTC).isoformat(),
    }


@router.get("/me")
def me(claims: dict = Depends(_get_claims)):
    return {
        "user_id": claims["sub"],
        "username": claims["username"],
        "role": claims["role"],
        "permissions": claims.get("permissions", []),
        "session_id": claims.get("sid"),
    }


@router.get("/protected/identity-read")
def protected_identity_read(claims: dict = Depends(_require_permission("identity:read"))):
    return {"status": "allowed", "user_id": claims["sub"]}


@router.get("/protected/identity-manage")
def protected_identity_manage(claims: dict = Depends(_require_permission("identity:manage"))):
    return {"status": "allowed", "user_id": claims["sub"]}


@router.get("/protected/health-read")
def protected_health_read(
    subject_user_id: str,
    scope: str = "health:read",
    claims: dict = Depends(_require_permission("health:read")),
):
    decision = consent_policy_evaluator.evaluate(
        actor_user_id=claims["sub"],
        actor_role=Role(claims["role"]),
        subject_user_id=subject_user_id,
        required_scope=scope,
        now=datetime.now(UTC),
    )
    if not decision:
        raise HTTPException(status_code=403, detail="Consent policy denied access")
    return {"status": "allowed", "subject_user_id": subject_user_id, "scope": scope}


@router.get("/permissions/me")
def my_permissions(claims: dict = Depends(_get_claims)):
    role = Role(claims["role"])
    return {"role": role.value, "permissions": sorted(role_permissions(role))}
