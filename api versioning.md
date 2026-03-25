apps/api/src/interfaces/api/
├─ router.py
├─ versioning.py                         # header/path strategy
├─ v1/
│  ├─ router.py
│  ├─ auth/
│  ├─ users/
│  ├─ family_linking/
│  ├─ health_records/
│  ├─ medications/
│  ├─ sos/
│  ├─ marketplace/
│  ├─ consent/
│  ├─ notifications/
│  ├─ subscriptions/
│  └─ analytics_admin/
├─ v2/
│  ├─ router.py
│  └─ ...                               # new contracts, backward-compat adapters
└─ compatibility/
   ├─ deprecations.py
   ├─ response_adapters.py
   └─ schema_migrations.py