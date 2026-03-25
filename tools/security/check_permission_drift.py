from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_SRC = REPO_ROOT / "apps" / "api"
sys.path.insert(0, str(API_SRC))

from src.modules.identity_access.models import ROLE_PERMISSIONS  # noqa: E402


def _normalize_permissions(values: set[str] | list[str]) -> list[str]:
    return sorted(set(values))


def main() -> int:
    baseline_path = REPO_ROOT / "tools" / "security" / "permission_matrix_baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    current = {
        role.value: _normalize_permissions(permissions)
        for role, permissions in ROLE_PERMISSIONS.items()
    }

    if baseline == current:
        print("Permission drift check passed")
        return 0

    print("Permission drift detected")
    all_roles = sorted(set(baseline) | set(current))
    for role in all_roles:
        expected = set(baseline.get(role, []))
        actual = set(current.get(role, []))
        added = sorted(actual - expected)
        removed = sorted(expected - actual)
        if not added and not removed:
            continue
        print(f"- Role: {role}")
        if added:
            print(f"  Added: {', '.join(added)}")
        if removed:
            print(f"  Removed: {', '.join(removed)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
