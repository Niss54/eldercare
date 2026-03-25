from src.modules.identity_access.models import User
from src.modules.identity_access.service import IdentityService, SessionState


class UserRepository:
    def __init__(self, users: dict[str, User]):
        self._users = users

    def get_by_email(self, email: str) -> User | None:
        return self._users.get(email)


class SessionRepository:
    def __init__(self, identity_service: IdentityService):
        self._identity_service = identity_service

    def get(self, session_id: str) -> SessionState | None:
        return self._identity_service.sessions.get(session_id)

    def revoke(self, session_id: str) -> None:
        self._identity_service.revoke_session(session_id)
