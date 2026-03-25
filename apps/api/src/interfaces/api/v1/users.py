from fastapi import APIRouter, Depends

from src.interfaces.api.v1.auth import DEMO_USERS
from src.middleware.auth import require_auth, require_role
from src.modules.identity_access.models import Role

router = APIRouter(tags=["users"])


@router.get("/users/me")
def users_me(claims: dict = Depends(require_auth)):
    return {
        "user_id": claims["sub"],
        "username": claims["username"],
        "role": claims["role"],
        "permissions": claims.get("permissions", []),
        "session_id": claims.get("sid"),
    }


@router.get("/admin/users")
def admin_users(_: dict = Depends(require_role(Role.admin))):
    users = [
        {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value,
        }
        for user in DEMO_USERS.values()
    ]
    return {"count": len(users), "items": users}
