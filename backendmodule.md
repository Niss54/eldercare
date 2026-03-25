apps/api/
├─ pyproject.toml
├─ alembic.ini
├─ alembic/
├─ src/
│  ├─ main.py
│  ├─ app/
│  │  ├─ bootstrap.py                    # DI/container wiring
│  │  ├─ settings.py
│  │  ├─ logging.py
│  │  ├─ exceptions.py
│  │  └─ lifespan.py
│  ├─ shared/
│  │  ├─ kernel/
│  │  │  ├─ entity.py
│  │  │  ├─ value_object.py
│  │  │  ├─ aggregate.py
│  │  │  ├─ domain_event.py
│  │  │  └─ repository.py
│  │  ├─ cqrs/
│  │  ├─ idempotency/
│  │  ├─ pagination/
│  │  └─ utils/
│  ├─ interfaces/                        # presentation/inbound
│  │  ├─ api/
│  │  │  ├─ dependencies/
│  │  │  ├─ middlewares/
│  │  │  ├─ v1/
│  │  │  │  ├─ auth/
│  │  │  │  ├─ users/
│  │  │  │  ├─ family_linking/
│  │  │  │  ├─ health_records/
│  │  │  │  ├─ medications/
│  │  │  │  ├─ sos/
│  │  │  │  ├─ marketplace/
│  │  │  │  ├─ consent/
│  │  │  │  ├─ notifications/
│  │  │  │  ├─ subscriptions/
│  │  │  │  ├─ analytics_admin/
│  │  │  │  └─ websockets/
│  │  │  └─ v2/                          # forward-compatible version slot
│  │  └─ websocket/
│  │     ├─ gateway.py
│  │     ├─ connection_manager.py
│  │     └─ channels/
│  ├─ modules/                           # bounded contexts (extractable services)
│  │  ├─ identity_access/
│  │  │  ├─ domain/
│  │  │  ├─ application/
│  │  │  ├─ infrastructure/
│  │  │  └─ contracts/
│  │  ├─ family_parent_linking/
│  │  ├─ health_records/
│  │  ├─ medication_reminders/
│  │  ├─ sos_alerting/
│  │  ├─ caregiver_marketplace/
│  │  ├─ consent_access/
│  │  ├─ notifications/
│  │  ├─ subscriptions/
│  │  ├─ admin_analytics/
│  │  ├─ audit_logging/
│  │  ├─ ai_integration/
│  │  └─ iot_integration/
│  ├─ integrations/                      # outbound adapters
│  │  ├─ db/
│  │  ├─ redis/
│  │  ├─ s3/
│  │  ├─ email/
│  │  ├─ sms/
│  │  ├─ push/
│  │  ├─ payment/
│  │  ├─ video/
│  │  └─ telemetry/
│  └─ tests/
│     ├─ unit/
│     ├─ integration/
│     └─ contract/
└─ migrations/