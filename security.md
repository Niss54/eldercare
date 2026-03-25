apps/api/src/modules/identity_access/
├─ domain/
│  ├─ entities/
│  ├─ roles.py                           # admin, family_member, parent, caregiver, doctor
│  ├─ permissions.py
│  └─ services/
├─ application/
│  ├─ commands/
│  ├─ queries/
│  ├─ use_cases/
│  └─ policies/
├─ infrastructure/
│  ├─ password_hashing/
│  ├─ token_service/                     # JWT/refresh
│  ├─ mfa/
│  ├─ oauth/
│  ├─ session_store/
│  └─ repositories/
└─ contracts/

apps/api/src/modules/consent_access/
├─ domain/
│  ├─ consent_grant.py
│  ├─ consent_scope.py
│  └─ access_decision.py
├─ application/
├─ infrastructure/
└─ contracts/

apps/api/src/modules/audit_logging/
├─ domain/
├─ application/
├─ infrastructure/
│  ├─ append_only_store/
│  └─ tamper_evidence/
└─ contracts/

apps/api/src/interfaces/api/middlewares/
├─ auth_middleware.py
├─ authorization_middleware.py
├─ consent_enforcement_middleware.py
├─ rate_limit_middleware.py
├─ security_headers_middleware.py
└─ request_signature_middleware.py