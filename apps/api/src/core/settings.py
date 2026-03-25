from functools import lru_cache
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "eldercare-platform"
    app_env: str = "development"
    api_port: int = 8000
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://eldercare_user:eldercare_pass@localhost:5432/eldercare"
    database_read_url: Optional[str] = None
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800
    slow_query_budget_ms: int = 200
    redis_url: str = "redis://localhost:6379/0"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    jwt_secret_key: str = "local-dev-jwt-secret-key-min-32-chars"
    jwt_refresh_secret_key: str = "local-dev-jwt-refresh-secret-key-min-32-chars"
    jwt_signing_keys: str = ""
    jwt_refresh_signing_keys: str = ""
    jwt_active_kid: str = "v1"
    jwt_refresh_active_kid: str = "v1"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    cors_allowed_origins: str = "http://localhost:3000"
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    auth_rate_limit_per_minute: int = 60
    sos_rate_limit_per_minute: int = 30
    health_records_rate_limit_per_minute: int = 45
    marketplace_rate_limit_per_minute: int = 60
    audit_rate_limit_per_minute: int = 30
    csrf_protected_paths: str = "/api/v1/auth,/api/v1/consent,/api/v1/health-records"
    secret_manager_provider: str = "env"
    secret_manager_kms_key_ref: str = ""
    otel_enabled: bool = False
    otel_service_name: str = "eldercare-api"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318/v1/traces"
    consent_cache_ttl_seconds: int = 300

    @model_validator(mode="after")
    def validate_runtime_secrets(self):
        non_local_envs = {"staging", "production", "prod", "qa", "uat"}
        normalized_env = self.app_env.strip().lower()
        placeholder_values = {
            "",
            "change-me",
            "change-me-too",
            "local-dev-jwt-secret-key-min-32-chars",
            "local-dev-jwt-refresh-secret-key-min-32-chars",
        }

        if normalized_env in non_local_envs:
            if self.secret_manager_provider.strip().lower() == "env":
                raise ValueError("secret_manager_provider must not be 'env' for non-local environments")
            if self.jwt_secret_key.strip() in placeholder_values:
                raise ValueError("jwt_secret_key must be sourced from secret manager in non-local environments")
            if self.jwt_refresh_secret_key.strip() in placeholder_values:
                raise ValueError("jwt_refresh_secret_key must be sourced from secret manager in non-local environments")

        if len(self.jwt_secret_key.strip()) < 32:
            raise ValueError("jwt_secret_key must be at least 32 characters")
        if len(self.jwt_refresh_secret_key.strip()) < 32:
            raise ValueError("jwt_refresh_secret_key must be at least 32 characters")

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
