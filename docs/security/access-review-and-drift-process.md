# Access Review and Permission Drift Process

## Review Cadence
- Weekly automated drift check in CI.
- Monthly manual access review by security owner and platform admin.
- Immediate ad-hoc review after security incidents.

## Automated Drift Check
- Script: tools/security/check_permission_drift.py
- Baseline: tools/security/permission_matrix_baseline.json
- Behavior: fails CI if role permission matrix differs from approved baseline.

## Manual Review Checklist
- Verify active roles match business requirements.
- Verify privileged roles (admin/doctor) still require MFA.
- Verify audit access permission is restricted to approved operators.
- Verify service accounts and automation users have least privilege.
- Verify emergency access actions are documented and audited.

## Approval Flow for Permission Changes
1. Propose permission change in PR with rationale.
2. Update baseline file and add tests for newly protected/authorized endpoints.
3. Obtain security owner approval.
4. Merge only after CI drift and test checks pass.
