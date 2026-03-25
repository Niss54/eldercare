import os


def resolve_secret(value: str) -> str:
    """Resolve plain or secret-manager referenced values.

    Supported local format:
    - plain secret value
    - sm://SECRET_NAME -> reads from env var SM_SECRET_NAME
    """
    if not value.startswith("sm://"):
        return value

    secret_name = value.removeprefix("sm://").strip()
    if not secret_name:
        raise ValueError("Invalid secret reference")

    env_key = f"SM_{secret_name}"
    resolved = os.getenv(env_key)
    if not resolved:
        raise ValueError(f"Secret manager reference not found: {env_key}")
    return resolved
