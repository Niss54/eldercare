import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.secrets import resolve_secret
from src.core.settings import Settings
from src.modules.identity_access.models import User, role_permissions

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


@dataclass(slots=True)
class SessionState:
    session_id: str
    user_id: str
    refresh_jti: str
    revoked: bool = False


class IdentityService:
    def __init__(self, settings: Settings, users: dict[str, User]):
        self.settings = settings
        self.users = users
        self.sessions: dict[str, SessionState] = {}
        self.revoked_refresh_jtis: set[str] = set()
        self.access_keyring = self._build_keyring(
            self.settings.jwt_signing_keys,
            fallback_key=self.settings.jwt_secret_key,
            default_kid=self.settings.jwt_active_kid,
        )
        self.refresh_keyring = self._build_keyring(
            self.settings.jwt_refresh_signing_keys,
            fallback_key=self.settings.jwt_refresh_secret_key,
            default_kid=self.settings.jwt_refresh_active_kid,
        )

    @staticmethod
    def _build_keyring(key_spec: str, fallback_key: str, default_kid: str) -> dict[str, str]:
        keyring: dict[str, str] = {}
        for item in key_spec.split(","):
            item = item.strip()
            if not item:
                continue
            if ":" not in item:
                continue
            kid, key = item.split(":", 1)
            kid = kid.strip()
            key = key.strip()
            if kid and key:
                keyring[kid] = resolve_secret(key)
        if default_kid not in keyring:
            keyring[default_kid] = resolve_secret(fallback_key)
        return keyring

    @staticmethod
    def _decode_with_keyring(token: str, keyring: dict[str, str], algorithm: str) -> dict:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if isinstance(kid, str) and kid in keyring:
            return jwt.decode(token, keyring[kid], algorithms=[algorithm])

        decode_error: JWTError | None = None
        for key in keyring.values():
            try:
                return jwt.decode(token, key, algorithms=[algorithm])
            except JWTError as exc:
                decode_error = exc
        if decode_error:
            raise decode_error
        raise JWTError("No signing keys configured")

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.users.get(username)
        if not user:
            return None
        if not pwd_context.verify(password, user.password_hash):
            return None
        return user

    def issue_token_pair(self, user: User, existing_session_id: str | None = None) -> dict[str, str | int | list[str]]:
        now = datetime.now(UTC)
        session_id = existing_session_id or secrets.token_urlsafe(18)
        refresh_jti = secrets.token_urlsafe(18)

        access_exp = now + timedelta(minutes=self.settings.access_token_expire_minutes)
        refresh_exp = now + timedelta(days=self.settings.refresh_token_expire_days)

        permissions = sorted(role_permissions(user.role))
        access_payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "permissions": permissions,
            "sid": session_id,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(access_exp.timestamp()),
        }
        refresh_payload = {
            "sub": user.id,
            "sid": session_id,
            "jti": refresh_jti,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(refresh_exp.timestamp()),
        }

        access_token = jwt.encode(
            access_payload,
            self.access_keyring[self.settings.jwt_active_kid],
            algorithm=self.settings.jwt_algorithm,
            headers={"kid": self.settings.jwt_active_kid},
        )
        refresh_token = jwt.encode(
            refresh_payload,
            self.refresh_keyring[self.settings.jwt_refresh_active_kid],
            algorithm=self.settings.jwt_algorithm,
            headers={"kid": self.settings.jwt_refresh_active_kid},
        )

        self.sessions[session_id] = SessionState(session_id=session_id, user_id=user.id, refresh_jti=refresh_jti)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(timedelta(minutes=self.settings.access_token_expire_minutes).total_seconds()),
            "role": user.role.value,
            "permissions": permissions,
            "session_id": session_id,
        }

    def decode_access_token(self, token: str) -> dict:
        payload = self._decode_with_keyring(token, self.access_keyring, self.settings.jwt_algorithm)
        if payload.get("type") != "access":
            raise JWTError("invalid token type")
        session_id = payload.get("sid")
        if not isinstance(session_id, str):
            raise JWTError("invalid session id")
        session = self.sessions.get(session_id)
        if not session or session.revoked:
            raise JWTError("session is revoked")
        return payload

    def rotate_refresh_token(self, refresh_token: str) -> tuple[User, dict[str, str | int | list[str]]]:
        payload = self._decode_with_keyring(refresh_token, self.refresh_keyring, self.settings.jwt_algorithm)
        if payload.get("type") != "refresh":
            raise JWTError("invalid token type")

        session_id = payload.get("sid")
        if not isinstance(session_id, str):
            raise JWTError("invalid session id")
        jti = payload.get("jti")
        if not isinstance(jti, str):
            raise JWTError("invalid refresh token id")
        if jti in self.revoked_refresh_jtis:
            raise JWTError("refresh token revoked")
        session = self.sessions.get(session_id)
        if not session or session.revoked:
            raise JWTError("session is revoked")
        if session.refresh_jti != jti:
            raise JWTError("refresh token was rotated")

        user = next((u for u in self.users.values() if u.id == session.user_id), None)
        if not user:
            raise JWTError("user not found")

        self.revoked_refresh_jtis.add(jti)
        tokens = self.issue_token_pair(user, existing_session_id=session_id)
        return user, tokens

    def revoke_refresh_token(self, refresh_token: str) -> None:
        payload = self._decode_with_keyring(refresh_token, self.refresh_keyring, self.settings.jwt_algorithm)
        if payload.get("type") != "refresh":
            raise JWTError("invalid token type")
        jti = payload.get("jti")
        if not isinstance(jti, str):
            raise JWTError("invalid refresh token id")
        self.revoked_refresh_jtis.add(jti)

    def revoke_session(self, session_id: str) -> None:
        session = self.sessions.get(session_id)
        if session:
            session.revoked = True


def hash_password(password: str) -> str:
    return pwd_context.hash(password)
