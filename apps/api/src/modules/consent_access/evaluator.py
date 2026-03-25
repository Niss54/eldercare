from datetime import UTC, datetime, timedelta

import redis

from src.core.settings import get_settings
from src.modules.consent_access.policy import ConsentDecisionInput, evaluate_consent_access
from src.modules.consent_access.service import consent_service
from src.modules.identity_access.models import Role


class ConsentPolicyEvaluator:
    def __init__(self, ttl_seconds: int | None = None):
        settings = get_settings()
        self.ttl_seconds = ttl_seconds or max(1, settings.consent_cache_ttl_seconds)
        self._settings = settings
        self.cache: dict[tuple[str, str, str], tuple[datetime, bool]] = {}
        self._redis_client: redis.Redis | None = None

    def _redis(self) -> redis.Redis | None:
        if self._redis_client is not None:
            return self._redis_client
        try:
            self._redis_client = redis.Redis.from_url(self._settings.redis_url, decode_responses=True)
        except Exception:
            self._redis_client = None
        return self._redis_client

    def _cache_key(self, actor_user_id: str, subject_user_id: str, required_scope: str) -> tuple[str, str, str]:
        return actor_user_id, subject_user_id, required_scope

    def _redis_key(self, actor_user_id: str, subject_user_id: str, required_scope: str) -> str:
        return f"consent:{actor_user_id}:{subject_user_id}:{required_scope}"

    def invalidate(self, subject_user_id: str | None = None, accessor_user_id: str | None = None) -> None:
        if not subject_user_id and not accessor_user_id:
            self.cache.clear()
            client = self._redis()
            if client is not None:
                try:
                    keys = list(client.scan_iter(match="consent:*"))
                    if keys:
                        client.delete(*keys)
                except Exception:
                    pass
            return

        keys_to_drop: list[tuple[str, str, str]] = []
        for key in self.cache:
            actor_user_id, cached_subject_user_id, _ = key
            if subject_user_id and cached_subject_user_id != subject_user_id:
                continue
            if accessor_user_id and actor_user_id != accessor_user_id:
                continue
            keys_to_drop.append(key)

        for key in keys_to_drop:
            self.cache.pop(key, None)

        client = self._redis()
        if client is None:
            return
        try:
            if subject_user_id and accessor_user_id:
                pattern = f"consent:{accessor_user_id}:{subject_user_id}:*"
            elif subject_user_id:
                pattern = f"consent:*:{subject_user_id}:*"
            else:
                pattern = f"consent:{accessor_user_id}:*:*"
            redis_keys = list(client.scan_iter(match=pattern))
            if redis_keys:
                client.delete(*redis_keys)
        except Exception:
            pass

    def evaluate(
        self,
        actor_user_id: str,
        actor_role: Role,
        subject_user_id: str,
        required_scope: str,
        now: datetime | None = None,
        cache_bypass: bool = False,
    ) -> bool:
        now = now or datetime.now(UTC)
        key = self._cache_key(actor_user_id=actor_user_id, subject_user_id=subject_user_id, required_scope=required_scope)
        redis_key = self._redis_key(actor_user_id=actor_user_id, subject_user_id=subject_user_id, required_scope=required_scope)

        if not cache_bypass:
            cached = self.cache.get(key)
            if cached and cached[0] > now:
                if not cached[1]:
                    return False
                if actor_role == Role.admin or actor_user_id == subject_user_id:
                    return True
                current_scopes = consent_service.granted_scopes_for(
                    subject_user_id=subject_user_id,
                    accessor_user_id=actor_user_id,
                    now=now,
                ).union(
                    consent_service.active_break_glass_scopes_for(
                        actor_user_id=actor_user_id,
                        subject_user_id=subject_user_id,
                        now=now,
                    )
                )
                domain_wildcard = None
                if ":" in required_scope:
                    domain, _ = required_scope.split(":", 1)
                    domain_wildcard = f"{domain}:*"
                if required_scope in current_scopes or "*:*" in current_scopes or (domain_wildcard and domain_wildcard in current_scopes):
                    return True

            client = self._redis()
            if client is not None:
                try:
                    cached_value = client.get(redis_key)
                except Exception:
                    cached_value = None
                if cached_value in {"0", "1"}:
                    if cached_value == "0":
                        return False
                    if actor_role == Role.admin or actor_user_id == subject_user_id:
                        return True
                    current_scopes = consent_service.granted_scopes_for(
                        subject_user_id=subject_user_id,
                        accessor_user_id=actor_user_id,
                        now=now,
                    ).union(
                        consent_service.active_break_glass_scopes_for(
                            actor_user_id=actor_user_id,
                            subject_user_id=subject_user_id,
                            now=now,
                        )
                    )
                    domain_wildcard = None
                    if ":" in required_scope:
                        domain, _ = required_scope.split(":", 1)
                        domain_wildcard = f"{domain}:*"
                    if required_scope in current_scopes or "*:*" in current_scopes or (
                        domain_wildcard and domain_wildcard in current_scopes
                    ):
                        return True

        granted_scopes = consent_service.granted_scopes_for(
            subject_user_id=subject_user_id,
            accessor_user_id=actor_user_id,
            now=now,
        )
        break_glass_scopes = consent_service.active_break_glass_scopes_for(
            actor_user_id=actor_user_id,
            subject_user_id=subject_user_id,
            now=now,
        )
        merged_scopes = granted_scopes.union(break_glass_scopes)

        allowed = evaluate_consent_access(
            ConsentDecisionInput(
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                subject_user_id=subject_user_id,
                required_scope=required_scope,
                granted_scopes=merged_scopes,
                now=now,
            )
        )
        self.cache[key] = (now + timedelta(seconds=self.ttl_seconds), allowed)
        client = self._redis()
        if client is not None:
            try:
                client.setex(redis_key, self.ttl_seconds, "1" if allowed else "0")
            except Exception:
                pass
        return allowed


consent_policy_evaluator = ConsentPolicyEvaluator()
