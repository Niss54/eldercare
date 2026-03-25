# Eldercare Remote Monitoring Platform

Production-grade platform for remote eldercare coordination across families, caregivers, and clinicians.

This repository is structured as a clean-architecture modular monolith with clear bounded contexts so each module can be extracted into microservices later with minimal refactor.

## Project Overview

The platform supports:
- Multi-role authentication: admin, family member, parent, caregiver, doctor
- Family-parent linking workflows
- Health record storage and retrieval
- Medication reminder orchestration
- SOS emergency cascade alerting
- Caregiver discovery and engagement marketplace
- Consent-based access control for PHI data
- Immutable audit logging for compliance and forensics
- Multi-channel notifications (email, SMS, push, in-app)
- Subscription and entitlement readiness
- Admin analytics and operational monitoring
- AI and IoT integration readiness layers

Core stack:
- Frontend: Next.js (React)
- Backend: FastAPI (Python)
- Database: PostgreSQL
- Queue: Celery + Redis
- Realtime: WebSockets
- Object Storage: S3-compatible
- Deployment: Docker-first

## System Architecture Explanation

High-level architecture pattern:
- Next.js app provides role-based UI and session-aware navigation.
- FastAPI backend exposes versioned REST APIs and WebSocket gateways.
- PostgreSQL stores transactional and relational domain data.
- Redis backs Celery broker/result backend and fast ephemeral state.
- Celery workers execute async jobs (notifications, reminders, analytics rollups).
- Celery beat scheduler dispatches periodic jobs (med windows, consent expiry checks).
- S3-compatible storage holds documents and media artifacts.
- Monitoring stack collects metrics, logs, traces, and alerts.

Design principles:
- Clean architecture separation: domain, application, infrastructure, interfaces
- Bounded contexts per business capability
- Strict contracts and API versioning
- Security by default (RBAC, consent checks, audit trail)
- Event-driven async workflows for reliability and scalability

## Backend Architecture Explanation

Backend layout is organized under module boundaries:
- `src/modules/*` contains domain-centric bounded contexts:
  - `identity_access`
  - `family_parent_linking`
  - `health_records`
  - `medication_reminders`
  - `sos_alerting`
  - `caregiver_marketplace`
  - `consent_access`
  - `notifications`
  - `subscriptions`
  - `admin_analytics`
  - `audit_logging`
  - `ai_integration`
  - `iot_integration`
- `src/interfaces/api/v1` and `src/interfaces/api/v2` provide versioned endpoint surfaces.
- `src/interfaces/websocket` manages realtime channels and auth.
- `src/integrations` contains adapters for DB, Redis, S3, email, SMS, push, payment, telemetry.
- `src/shared` provides kernel utilities (entity patterns, CQRS helpers, idempotency, pagination).

Each module follows clean architecture layers:
- Domain: business rules, aggregates, value objects, domain services
- Application: use-cases, commands/queries, orchestration logic
- Infrastructure: repositories, providers, external adapters
- Contracts: DTOs/events for internal and external integration

## Frontend Architecture Explanation

Frontend (Next.js App Router) is organized by role and feature:
- Route groups: `(public)`, `(auth)`, `(admin)`, `(family)`, `(parent)`, `(caregiver)`, `(doctor)`
- Feature modules: auth, family-linking, health-records, medications, sos, marketplace, consent, notifications, subscriptions, analytics
- Shared layer: UI components, forms, state management, API client, websocket client, guards, config

Frontend principles:
- Role-aware routing and guard components
- Feature-sliced modules to reduce coupling
- Typed API client contracts
- Optimistic UX for reminders and notifications
- Progressive enhancement for realtime and offline states

## Backend Capability vs UI Wiring Status

The backend includes broader capability than currently exposed in UI screens. Use this matrix when planning frontend integration work.

| Module | Backend Capability Implemented | UI Wired Status | Notes |
|---|---|---|---|
| auth | Yes | Partial | login/logout and MFA challenge wired; refresh/profile recovery flows pending |
| users | Yes | Not Wired | backend endpoints implemented but no active portal integration |
| health-records | Yes | Wired | list/create/search and signed document download wired |
| consent | Yes | Partial | scopes/grants/revoke/evidence wired; admin review flows pending |
| family-links | Yes | Not Wired | relationship endpoints not yet connected to active portal screens |
| medication | Yes | Not Wired | backend scheduling and metrics exist; no family portal wiring yet |
| marketplace | Yes | Partial | caregiver list and booking wired; moderation/verification flows pending |
| notifications | Yes | Wired | history, preferences, send, realtime reconciliation wired |
| sos | Yes | Wired | trigger/list/timeline and realtime timeline reconciliation wired |
| subscriptions | Yes | Partial | plans/entitlements/checkout wired; lifecycle and invoice flows pending |
| admin-analytics | Yes | Wired | dashboard, actions, feature flags, export wired |
| audit | Yes | Not Wired | compliance endpoints not yet connected to web UI |
| realtime (REST) | Yes | Not Wired | websocket paths wired; REST realtime query endpoints mostly unused |

Reference details: see `BACKEND_FRONTEND_CONTRACT_MAP.md`.

## Database Structure Overview

PostgreSQL is organized by bounded domain models and read models:
- Identity and access: users, roles, permissions, sessions
- Family linking: invites, links, approvals, relationship state history
- Consent: grants, scopes, revocations, expiry, emergency override logs
- Health records: metadata, categories, object-storage pointers, provenance
- Medication: prescriptions, schedules, reminders, adherence, escalation events
- SOS: incidents, responders, acknowledgements, escalation hops, resolution timeline
- Notifications: templates, preferences, deliveries, provider receipts
- Marketplace: caregiver profiles, credentials, availability, bookings, reviews
- Subscription: plans, entitlements, billing events, subscription states
- Audit: append-only event log with tamper-evidence fields
- Analytics: rollups and denormalized read models

Data governance:
- RLS and consent filters on sensitive access paths
- Migration-driven schema evolution (Alembic)
- Backup and restore validation scripts

## Worker Architecture

Celery-based asynchronous processing:
- `apps/worker` executes background tasks:
  - notifications dispatch
  - medication reminders and escalations
  - SOS cascade retries
  - analytics rollups
  - audit exports
  - subscription billing tasks
  - future AI/IoT jobs
- `apps/scheduler` (Celery Beat) triggers periodic workflows:
  - medication windows
  - reminder escalations
  - stale SOS watchdog
  - consent expiry checks
  - subscription renewals
  - analytics snapshots

Reliability controls:
- Task idempotency keys
- Retry with exponential backoff
- Dead-letter handling
- Queue-level priority routing
- Operational metrics and alerting

## WebSocket Architecture

Realtime messaging is implemented in backend interface layer:
- Authenticated handshake with token verification
- Channel-level authorization based on role + consent
- Connection manager with presence/session tracking
- Domain channels:
  - notifications
  - SOS incidents
  - medication updates
  - caregiver interactions
  - admin operations
- Event serialization contracts for outbound/inbound payloads

Usage:
- Instant SOS incident visibility and acknowledgement updates
- Live notification feed synchronization
- Near-realtime care operations dashboards

## Security Architecture

Security model combines identity, authorization, consent, and observability:
- Authentication: JWT access and refresh lifecycle
- Authorization: RBAC + resource checks
- Consent enforcement: policy decision and policy enforcement at API and websocket boundaries
- Input and output validation: strict schema validation
- Transport security: HTTPS/TLS across services
- Secrets management: environment segregation and key rotation
- Platform controls: rate limiting, security headers, abuse detection
- Data security: encryption at rest and in transit

## RBAC Role Explanation

Platform roles and default responsibilities:
- Admin:
  - Tenant/platform administration
  - Analytics visibility
  - Operational controls and compliance review
- Family Member:
  - Linked parent profile management
  - Medication oversight
  - SOS responder workflow
- Parent:
  - Own health data visibility
  - Consent management and preferences
- Caregiver:
  - Assigned care tasks and updates
  - Availability and service delivery workflows
- Doctor:
  - Clinical oversight views
  - Documentation and treatment guidance

RBAC notes:
- Role membership grants baseline capabilities.
- Fine-grained resource checks and consent policies still apply.
- Sensitive operations always produce audit events.

## Consent-Based Data-Sharing Explanation

Consent engine governs who can access what data and when:
- Consent scope includes data domain, action, principal, and validity window.
- Access is evaluated at request time for API and websocket paths.
- Revocations take effect immediately.
- Expiry is enforced by scheduler jobs.
- Break-glass emergency access is isolated, time-bound, and fully audited.

Outcome:
- Family, caregiver, and doctor access is policy-controlled and traceable.
- Compliance posture is maintained without blocking emergency operations.

## Audit Logging System Explanation

Audit logging is append-only and compliance-oriented:
- Captures authentication, access decisions, PHI reads/writes, consent actions, SOS transitions, admin actions
- Stores actor, action, resource, context, correlation IDs, and timestamps
- Supports tamper-evidence using event-chain metadata
- Exposes filtered query APIs for compliance and incident forensics
- Supports retention, archival, and secure export workflows

## Required API Keys and External Integrations

Add keys to secure secret stores and environment files per environment.

Communication:
- Email service: SMTP credentials or SendGrid API key
- SMS gateway: Twilio or MSG91 credentials
- Push notifications: Firebase project/service account
- WhatsApp readiness: Meta WhatsApp Cloud API tokens

Storage and location:
- Object storage: AWS S3 (or compatible endpoint + credentials)
- Maps/location: Google Maps API key

Consultation and payments:
- Video consultation readiness: WebRTC signaling config or Agora credentials
- Payment gateway readiness: Razorpay or Stripe API credentials

Observability and product analytics:
- Error monitoring: Sentry DSN and auth token
- Product analytics: PostHog or Mixpanel project credentials

## Environment Variables Example

Use `.env` for local setup. Keep production secrets in a managed secret store.

```env
# App
APP_ENV=development
APP_NAME=eldercare-platform
APP_PORT=8000
WEB_PORT=3000
API_BASE_URL=http://localhost:8000
WEB_BASE_URL=http://localhost:3000

# Security
JWT_SECRET_KEY=change-me
JWT_REFRESH_SECRET_KEY=change-me-too
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=14

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=eldercare
POSTGRES_USER=eldercare_user
POSTGRES_PASSWORD=eldercare_pass
DATABASE_URL=postgresql+psycopg://eldercare_user:eldercare_pass@localhost:5432/eldercare

# Redis and Celery
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Object Storage (S3-compatible)
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_REGION=ap-south-1
S3_BUCKET=eldercare-docs
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key

# Email (SMTP or SendGrid)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAIL_FROM=no-reply@example.com

# SMS (Twilio or MSG91)
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_FROM_NUMBER=+10000000000
MSG91_AUTH_KEY=optional-if-using-msg91

# Push (Firebase)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CLIENT_EMAIL=service-account@project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# WhatsApp (Meta)
WHATSAPP_META_TOKEN=your-meta-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id

# Maps
GOOGLE_MAPS_API_KEY=your-google-maps-key

# Video readiness
AGORA_APP_ID=optional
AGORA_APP_CERTIFICATE=optional
WEBRTC_SIGNALING_URL=optional

# Payment readiness
STRIPE_SECRET_KEY=optional
STRIPE_WEBHOOK_SECRET=optional
RAZORPAY_KEY_ID=optional
RAZORPAY_KEY_SECRET=optional

# Monitoring and Analytics
SENTRY_DSN=your-sentry-dsn
POSTHOG_API_KEY=optional
POSTHOG_HOST=https://app.posthog.com
MIXPANEL_TOKEN=optional

# Feature flags
FEATURE_AI_INTEGRATION=false
FEATURE_IOT_INTEGRATION=false
```

## Local Development Setup

Prerequisites:
- Node.js LTS
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+ (if running outside containers)
- Redis 7+ (if running outside containers)

1. Clone repository and move into project root.
2. Create local env file from example and update values.
3. Start dependencies (PostgreSQL, Redis, object storage) using Docker Compose.
4. Start backend API service.
5. Start worker and scheduler processes.
6. Start frontend app.
7. Run migrations and seed baseline data.
8. Verify health checks and smoke tests.

Example command flow:
```bash
# dependencies
cd infra/compose
docker compose -f docker-compose.dev.yml up -d postgres redis minio

# backend
cd ../../apps/api
pip install -e .
alembic upgrade head
uvicorn src.main:app --reload --port 8000

# worker
cd ../worker
pip install -e .
celery -A src.celery_app worker -l info

# scheduler
cd ../scheduler
pip install -e .
celery -A src.beat beat -l info

# frontend
cd ../web
npm install
npm run dev
```

## Docker Setup Instructions

Repository includes container build and orchestration paths:
- Dockerfiles:
  - `infra/docker/api.Dockerfile`
  - `infra/docker/web.Dockerfile`
  - `infra/docker/worker.Dockerfile`
  - `infra/docker/scheduler.Dockerfile`
  - `infra/docker/nginx.Dockerfile`
- Compose files:
  - `infra/compose/docker-compose.dev.yml`
  - `infra/compose/docker-compose.staging.yml`
  - `infra/compose/docker-compose.prod.yml`

Typical startup:
```bash
cd infra/compose
docker compose -f docker-compose.dev.yml up --build
```

Recommended container standards:
- Multi-stage builds for minimal runtime images
- Non-root container users
- Read-only filesystem where possible
- Healthcheck endpoints enabled for all services

## Production Deployment Readiness Checklist

- [ ] Environment-specific configuration and secret management complete
- [ ] HTTPS/TLS certificates and renewal in place
- [ ] Zero-downtime migration strategy validated
- [ ] CI/CD gates include tests, lint, SAST, dependency scan, container scan
- [ ] Image signing and provenance verification enabled
- [ ] Autoscaling rules defined for API, workers, websocket gateway
- [ ] Backup and restore tested for DB and object storage
- [ ] Monitoring dashboards and pager alerts configured
- [ ] Incident runbooks prepared and reviewed
- [ ] Disaster recovery drill completed with RTO/RPO targets

## Security Hardening Checklist

- [ ] Strong password policy and MFA for privileged roles
- [ ] JWT key rotation process implemented
- [ ] Least-privilege RBAC + consent checks on all protected resources
- [ ] Request validation and response schema enforcement enabled
- [ ] Rate limits for auth, notification, and SOS endpoints
- [ ] CORS, CSP, HSTS, and secure headers configured
- [ ] Secrets never stored in repo; secret manager integration complete
- [ ] Database encryption at rest and TLS in transit
- [ ] Object storage bucket policy hardened and private by default
- [ ] Audit logging enabled for all sensitive operations
- [ ] Dependency patch cadence and vulnerability triage process active
- [ ] Access review and key rotation schedule documented

## Scaling Strategy

Scale path by bottleneck and business growth stage:
- API tier:
  - Horizontal scaling behind load balancer
  - Stateless app instances with centralized session/token strategy
- Worker tier:
  - Queue-per-domain routing
  - Independent worker pools for high-priority tasks (SOS, notifications)
- Database tier:
  - Read replicas for analytics and heavy reads
  - Partition high-volume tables (audit, notifications, incidents)
  - Connection pooling and query optimization
- WebSocket tier:
  - Sticky sessions or shared pub/sub for fanout
  - External broker for cross-instance event delivery
- Storage tier:
  - Lifecycle policies for archival and cost optimization
  - CDN for large media/download acceleration
- Observability and resilience:
  - SLO-based alerting
  - Circuit breakers and retry budgets
  - Backpressure controls for burst events

Microservice extraction readiness:
- Bounded contexts already isolated by module contracts
- Extract starting with high-churn domains (notifications, marketplace, analytics)
- Keep API gateway and contract versioning stable during split

## Future Roadmap: AI Monitoring and Wearable Integrations

AI monitoring roadmap:
- Phase A: AI-ready data pipelines and consent-safe feature stores
- Phase B: Clinical summary generation and anomaly detection assistants
- Phase C: Predictive risk scoring for missed meds and SOS probability
- Phase D: Human-in-the-loop decision workflows and explainability dashboards

Wearable integration roadmap:
- Phase A: Device registry and standardized telemetry ingestion contracts
- Phase B: Integrate baseline vitals from common wearable ecosystems
- Phase C: Real-time threshold alerts into notifications and SOS workflows
- Phase D: Longitudinal trend analytics and clinician-facing insights

Governance requirements for both tracks:
- Explicit consent scope extensions for AI and device data
- Transparent model and alert explainability
- Expanded audit trails for automated recommendations
- Safety review workflow before production rollout

## Repository Structure (Reference)

```text
eldercare-platform/
├─ apps/
│  ├─ web/
│  ├─ api/
│  ├─ worker/
│  └─ scheduler/
├─ libs/
│  ├─ contracts/
│  ├─ events/
│  ├─ authz-policy/
│  ├─ notifications-sdk/
│  └─ observability/
├─ infra/
│  ├─ docker/
│  ├─ compose/
│  ├─ k8s/
│  ├─ terraform/
│  ├─ monitoring/
│  ├─ secrets/
│  ├─ backup/
│  └─ disaster-recovery/
├─ docs/
├─ tools/
└─ .github/
```

## License

Proprietary startup repository unless otherwise specified.
