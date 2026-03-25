from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request

from src.interfaces.api.v1.auth import _get_claims
from src.modules.consent_access.evaluator import consent_policy_evaluator
from src.modules.identity_access.models import Role


def require_consent(required_scope: str):
    async def _dependency(request: Request, claims: dict = Depends(_get_claims)) -> None:
        subject_user_id = request.query_params.get("subject_user_id")

        if not subject_user_id and request.method in {"POST", "PUT", "PATCH"}:
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                subject_user_id = payload.get("subject_user_id")

        if not subject_user_id:
            raise HTTPException(status_code=400, detail="subject_user_id is required for consent check")

        allowed = consent_policy_evaluator.evaluate(
            actor_user_id=claims["sub"],
            actor_role=Role(claims["role"]),
            subject_user_id=subject_user_id,
            required_scope=required_scope,
            now=datetime.now(UTC),
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="Consent policy denied access")

    return _dependency
