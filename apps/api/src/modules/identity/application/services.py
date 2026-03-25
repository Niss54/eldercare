from jose import JWTError

from src.modules.identity_access.models import Role, role_permissions
from src.modules.identity_access.service import IdentityService, hash_password, pwd_context


class AuthenticationService:
    def __init__(self, identity_service: IdentityService):
        self.identity_service = identity_service

    def login(self, email: str, password: str) -> dict:
        user = self.identity_service.authenticate(email, password)
        if not user:
            raise ValueError("invalid credentials")
        return self.identity_service.issue_token_pair(user)

    def refresh(self, refresh_token: str) -> dict:
        try:
            _, token_pair = self.identity_service.rotate_refresh_token(refresh_token)
        except JWTError as exc:
            raise ValueError("invalid refresh token") from exc
        return token_pair

    def logout(self, session_id: str, refresh_token: str | None = None) -> None:
        self.identity_service.revoke_session(session_id)
        if refresh_token:
            self.identity_service.revoke_refresh_token(refresh_token)


class PasswordService:
    @staticmethod
    def hash_password(password: str) -> str:
        return hash_password(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)


class RoleService:
    @staticmethod
    def permissions_for_role(role: Role) -> set[str]:
        return role_permissions(role)
