apps/api/src/integrations/db/
├─ base/
│  ├─ metadata.py
│  ├─ session.py
│  └─ types.py
├─ models/
│  ├─ identity_access/
│  ├─ family_parent_linking/
│  ├─ health_records/
│  ├─ medication_reminders/
│  ├─ sos_alerting/
│  ├─ caregiver_marketplace/
│  ├─ consent_access/
│  ├─ notifications/
│  ├─ subscriptions/
│  ├─ admin_analytics/
│  └─ audit_logging/
├─ repositories/
│  ├─ identity_access/
│  ├─ family_parent_linking/
│  ├─ health_records/
│  ├─ medication_reminders/
│  ├─ sos_alerting/
│  ├─ caregiver_marketplace/
│  ├─ consent_access/
│  ├─ notifications/
│  ├─ subscriptions/
│  ├─ admin_analytics/
│  └─ audit_logging/
├─ readmodels/                           # denormalized query models
├─ migrations/
│  ├─ versions/
│  └─ seeds/
└─ policies/
   ├─ row_level_security.sql
   └─ consent_filters.sql