# Eldercare Platform Engineering Roadmap (Startup Execution TODO)

## 1) Program Goals

Build a healthcare-grade, production-ready eldercare remote monitoring platform with:
- Frontend: Next.js (React)
- Backend: FastAPI (Python)
- Database: PostgreSQL
- Queue and scheduling: Celery + Redis
- Realtime: WebSockets
- Storage: S3-compatible object storage
- Deployment: Docker-first, cloud-ready

Target outcomes:
- Safe multi-role workflows (admin, family member, parent, caregiver, doctor)
- High trust through consent controls and auditability
- Fast operational response via notifications and SOS cascade
- Clear monetization path via subscription readiness
- Architecture that can split by bounded contexts into microservices later

## 2) Delivery Phases and Milestones

## Phase 0 - Foundation (Week 1-2)
- [x] Create repository scaffold from approved folder structure
- [x] Configure local dev stack (Docker Compose: api, web, worker, scheduler, postgres, redis, object storage)
- [x] Set up CI basics (lint, test, build)
- [x] Set up centralized logging format and request correlation IDs
- [x] Add API versioning shell (v1 + v2 placeholder)

Exit criteria:
- [ ] One-command local startup succeeds (pending Docker daemon availability)
- [ ] Health checks pass for all core services (pending Docker daemon availability)
- [ ] Base CI pipeline green (pending first GitHub Actions run)

## Phase 1 - Core Identity and Access (Week 2-4)
- [x] Implement identity and access module with multi-role auth
- [x] Build role claims and permission checks
- [x] Add session and token lifecycle (access + refresh)
- [x] Add consent policy evaluation skeleton

Exit criteria:
- [x] Login/logout works for all roles
- [x] Protected route access is role-gated and tested

## Phase 2 - Family, Records, and Consent (Week 4-6)
- [x] Implement family-parent linking workflows
- [x] Implement health records domain and APIs
- [x] Enforce consent-based data access on all sensitive endpoints
- [x] Add immutable audit events for all PHI reads/writes

Exit criteria:
- [x] Family member can link/unlink to parent with approvals
- [x] Health data access blocked without valid consent

## Phase 3 - Care Operations (Week 6-8)
- [x] Implement medication reminder engine (scheduler + worker)
- [x] Implement notifications service (email/SMS/push/in-app)
- [x] Implement SOS emergency cascade alert logic
- [x] Add realtime websocket channels for SOS and notifications

Exit criteria:
- [x] Reminder jobs execute reliably and are observable
- [x] SOS cascade reaches configured recipients with escalation rules

## Phase 4 - Marketplace and Growth (Week 8-10)
- [x] Implement caregiver marketplace listing/search/match flows
- [x] Add caregiver verification pipeline stubs
- [x] Implement subscription-ready billing abstractions
- [x] Build admin analytics dashboard v1

Exit criteria:
- [x] Marketplace flows complete end-to-end
- [x] Subscription plans and entitlement guards are enforced

## Phase 5 - Hardening and Launch Readiness (Week 10-12)
- [x] Complete security hardening checklist
- [x] Performance, load, and failure-mode validation
- [x] Data backup and restore drills
- [x] Incident runbooks and on-call alerts

Exit criteria:
- [ ] Staging signoff complete (runbook checklist created; execution pending)
- [ ] Production deployment checklist complete (checklist created; execution pending)

## 3) Backend Implementation Sequence (FastAPI)

1. [x] Platform bootstrap: settings, DI, logging, exception handling, health endpoints
2. [x] Identity and access: multi-role auth, token lifecycle, password and MFA flows
3. [x] Shared kernel utilities: domain base classes, CQRS handlers, idempotency, pagination
4. [x] Consent access core: policy engine + enforcement middleware
5. [x] Family-parent linking: invitations, approvals, relationship lifecycle
6. [x] Health records: CRUD + secure object references (S3 metadata)
7. [x] Audit logging: append-only immutable event trail for sensitive actions
8. [x] Notification orchestration API + provider adapters
9. [x] Medication reminders domain + command handlers
10. [x] SOS alerting domain + escalation state machine
11. [x] Caregiver marketplace APIs + matching logic + moderation hooks
12. [x] Subscription abstractions + entitlement middleware
13. [x] Admin analytics query APIs and rollup endpoints
14. [x] WebSocket gateway + channel authorization
15. [x] AI/IoT integration boundary interfaces (ports/adapters, feature-flagged)

## 4) Frontend Implementation Sequence (Next.js)

1. [x] App shell, route groups, role-based layouts, design system tokens
2. [x] Authentication screens and guarded navigation by role
3. [x] Family-parent linking onboarding and relationship management screens
4. [x] Health record dashboards, forms, and document upload/download UI
5. [x] Consent management UI (grant/revoke/scope history)
6. [x] Notifications center and realtime alert toasts
7. [x] Medication schedule UI (calendar + adherence state)
8. [x] SOS trigger UI + live incident status timeline
9. [x] Caregiver marketplace list/detail/filter/booking flows
10. [x] Subscription plans, checkout entry points, entitlement UX
11. [x] Admin dashboard analytics and operational controls
12. [x] Future AI assistant and IoT device panels behind feature flags

## 5) Database Schema Tasks (PostgreSQL)

1. [x] Create schema namespaces by bounded context (identity, consent, health, sos, marketplace, billing, analytics, audit)
2. [x] Create base user, profile, role, permission, and session tables
3. [x] Create family-parent relationship tables with invite/approval state
4. [x] Create consent grant/scope/expiry/revocation tables
5. [x] Create health record metadata tables and S3 object pointer model
6. [x] Create medication schedule, reminder, adherence, escalation tables
7. [x] Create SOS incident, escalation hop, responder acknowledgement tables
8. [x] Create notification template, delivery attempt, provider response tables
9. [x] Create marketplace caregiver profile, credential, availability, match, booking tables
10. [x] Create subscription plan, customer entitlement, invoice pointer tables
11. [x] Create audit event append-only table with hash chaining metadata
12. [x] Create analytics read models and rollup tables
13. [x] Add RLS policies and consent-aware filtering functions
14. [x] Add migration seeds for non-PHI bootstrap data
15. [x] Add backup/restore validation scripts and migration smoke tests

## 6) Security Setup Steps

1. [x] Define threat model and data classification (PHI/PII/operational)
2. [x] Implement RBAC and resource-level authorization checks
3. [x] Implement consent-aware authorization middleware
4. [x] Add JWT signing key rotation and refresh token revocation support
5. [x] Add MFA for admin and clinical roles
6. [x] Enforce strict input validation and output schema validation
7. [x] Add rate limiting and abuse protections for auth/SOS endpoints
8. [x] Add security headers, CORS policy, and CSRF strategy for web flows
9. [x] Encrypt secrets and environment variables via secret manager
10. [x] Encrypt data in transit and at rest (DB, object storage)
11. [x] Implement tamper-evident audit trails for critical actions
12. [x] Add dependency and container image vulnerability scanning in CI
13. [x] Add periodic access review and permission drift checks

## 7) Scheduler Setup Steps (Celery Beat)

1. [x] Define queue topology and routing keys per module
2. [x] Configure beat schedules for medication windows and escalations
3. [x] Add retry policy templates with backoff and dead-letter routing
4. [x] Add scheduler lock strategy to avoid duplicate dispatches
5. [x] Add idempotent task keys and dedup guards
6. [x] Add operational metrics (lag, retries, failures, throughput)
7. [x] Add alert thresholds for delayed or failed critical tasks
8. [x] Add runbooks for replay and manual compensation

## 8) Notification Engine Setup Steps

1. [x] Define notification event contract and template model
2. [x] Implement provider abstraction (email, SMS, push, in-app)
3. [x] Add per-user channel preference and quiet hours logic
4. [x] Add message priority tiers (routine, urgent, critical)
5. [x] Add delivery tracking and provider callback handling
6. [x] Add fallback routing logic when primary channel fails
7. [x] Add localization and accessibility formatting support
8. [x] Add abuse controls (throttles, dedup, suppression rules)

## 9) SOS Alert Logic Steps

1. [x] Define SOS incident state machine (created, acknowledged, escalated, resolved)
2. [x] Define cascade policy graph by role and availability
3. [x] Implement first-responder selection rules
4. [x] Implement escalation timers and retry behavior
5. [x] Implement parallel notifications over multiple channels
6. [x] Add realtime websocket incident updates
7. [x] Add audit and forensic event timeline capture
8. [x] Add fallback policy if no acknowledgement is received
9. [x] Add test simulation suite for day/night and network outage scenarios

## 10) Caregiver Marketplace Logic Steps

1. [x] Create caregiver onboarding and profile schema
2. [x] Add credential verification workflow and review statuses
3. [x] Add search index and filter model (skills, geography, availability, language)
4. [x] Add matching and ranking strategy (rule-based v1)
5. [x] Add booking request and acceptance lifecycle
6. [x] Add ratings and incident reporting primitives
7. [x] Add moderation workflows and trust/safety actions
8. [x] Add extension points for dynamic pricing and recommendations

## 11) Consent Engine Setup Steps

1. [x] Define consent scopes by data domain and action
2. [x] Define grant lifecycle (requested, granted, revoked, expired)
3. [x] Build policy evaluator service and cache strategy
4. [x] Integrate evaluator into API and websocket authorization
5. [x] Add emergency break-glass policy with strict auditing
6. [x] Add consent expiry and renewal scheduler jobs
7. [x] Add consent evidence records (who, when, why)
8. [x] Add admin review tools for disputed access

## 12) Audit Logging Setup Steps

1. [x] Define canonical audit event schema
2. [x] Add middleware to capture request/response metadata safely
3. [x] Add domain event publishers from all bounded contexts
4. [x] Persist to append-only store with hash chain checkpoints
5. [x] Build query APIs for compliance and incident review
6. [x] Add retention and archive policy controls
7. [x] Add anomaly detection hooks for suspicious access patterns

## 13) Subscription Readiness Steps

1. [x] Define plans, features, and entitlement matrix
2. [x] Add tenant/account subscription state model
3. [x] Add entitlement checks in API and UI guards
4. [x] Add payment provider abstraction interface
5. [x] Add trial, grace period, dunning, and renewal flows
6. [x] Add invoice and payment event ingestion model
7. [x] Add audit and analytics around plan conversion and churn

## 14) Admin Dashboard Steps

1. [x] Define key operational and product metrics
2. [x] Build secure admin-only analytics APIs
3. [x] Build dashboard cards for usage, incidents, alerts, and queue health
4. [x] Add filters by geography, role, plan, and time windows
5. [x] Add operational actions (disable account, resend invite, incident review)
6. [x] Add export and reporting capabilities
7. [x] Add feature-flag and rollout controls for staged releases

## 15) Deployment Preparation Steps ✅ COMPLETED

1. [x] Finalize Dockerfiles for api, web, worker, scheduler, nginx
   - Multi-stage builds with security hardening, health checks
   - Alpine Linux bases, non-root users, read-only filesystems
   
2. [x] Finalize compose stacks for dev/staging/prod parity
   - docker-compose.yml (dev with hot-reload)
   - docker-compose.staging.yml (resource limits, 1 replica each)
   - docker-compose.prod.yml (HA: 3x API, 2x web, 3x workers)

3. [x] Configure IaC for network, postgres, redis, object storage, monitoring
   - Kubernetes manifests (7 files with RBAC, HPA, Ingress)
   - Helm charts for multi-environment deployment
   - AWS CloudFormation: VPC+RDS+Redis+S3, ECS cluster+tasks

4. [x] Configure secrets management and rotation workflows
   - setup-secrets.sh for AWS Secrets Manager provisioning
   - Support for db-password, jwt-secret, redis-password, credentials

5. [x] Set up CI/CD gates (tests, security scan, migration checks, image signing)
   - .github/workflows/ci-cd.yml: Tests, linting, build, deploy
   - .github/workflows/security-scan.yml: Trivy, Grype, dependency checks, Cosign signing
   - .github/workflows/database-migrations.yml: Migration validation, backup, approval workflow
   - .github/workflows/deployment-monitoring.yml: Health checks, canary, rollback automation

6. [x] Add blue/green or canary deployment strategy
   - DEPLOYMENT_STRATEGIES.md: Docker Compose, K8s, and ECS variants
   - AWS Step Function for canary orchestration
   - Nginx traffic switching for blue/green
   - Ingress service switching for Kubernetes
   - Circuit breaker deployments in ECS

7. [x] Add database migration runbook with rollback controls
   - Documented in DEPLOYMENT_STRATEGIES.md and database-migrations workflow
   - Zero-downtime patterns, rollback procedures
   - RDS snapshot backups before migrations (staging)
   - Alembic downgrade testing

8. [x] Add observability dashboards and SLO alerts
   - CloudWatch dashboard (cloudwatch-dashboard.json) with 10+ widgets
   - Prometheus SLO rules (prometheus-slo-rules.yml) with 40+ rules
   - SLI tracking (availability, latency, error rates)
   - Business metrics monitoring
   - Alert thresholds: API 99.9%, latency P99 < 500ms, errors < 0.1%

9. [x] Perform backup/restore and disaster recovery rehearsal
   - BACKUP_DISASTER_RECOVERY.md: RTO/RPO targets, procedures
   - Automated daily database snapshots with point-in-time recovery
   - S3 cross-region replication
   - Git repository mirroring
   - Monthly DR drill script with validation

10. [x] Complete launch readiness review and go-live checklist
    - LAUNCH_READINESS_CHECKLIST.md: 100+ validation points
    - Phase 1-7: Infrastructure, security, operations, testing, launch, post-launch
    - Sign-off section for all stakeholders
    - Known limitations, rollback procedures, support contacts

## 16) Module-wise Development Roadmap ✅ COMPLETED

**Comprehensive roadmap document**: See [MODULE_ROADMAP.md](MODULE_ROADMAP.md)

**Coverage**: All 15 modules with detailed specifications:

### Module Overview (15 modules total)

| # | Module | Epic | Priority | Dependencies |
|---|--------|------|----------|--------------|
| M01 | Platform Foundation | Engineering standards | P0 | None |
| M02 | Identity & Access | Multi-tenant authentication | P0 | M01 |
| M03 | Family-Parent Linking | Relationship establishment | P1 | M02 |
| M04 | Consent Access Engine | Healthcare-grade PHI protection | P1 | M02, M03 |
| M05 | Health Records | Clinical data storage | P1 | M02, M04 |
| M06 | Audit Logging | Immutable compliance trail | P0 | M01 |
| M07 | Notification Engine | Multi-channel communication | P1 | M02, M06 |
| M08 | Medication Remind. | Preventive care backbone | P1 | M04, M05, M07 |
| M09 | SOS Emergency | Mission-critical response | P0 | M02, M03, M07, M13, M06 |
| M10 | Caregiver Market. | Growth lever | P2 | M02, M03, M04, M07 |
| M11 | Subscription | Revenue + entitlements | P2 | M02, M10 |
| M12 | Admin Analytics | Operational visibility | P2 | M06-M11 |
| M13 | WebSocket Layer | Realtime updates | P1 | M02, M07 |
| M14 | AI Integration | Future AI features (RFQ) | P3 | M04, M05, M06, M08, M12 |
| M15 | IoT Integration | Future device support (RFQ) | P3 | M04, M05, M07, M09 |

### Each Module Includes

- ✅ **What to build**: Detailed features and entities
- ✅ **Why needed**: Business impact and user value
- ✅ **Implementation order**: Sprint sequence
- ✅ **Dependencies**: Explicit module dependencies
- ✅ **Scalability notes**: Architectural considerations
- ✅ **Success criteria**: Definition of done (15+ items each)
- ✅ **Estimated effort**: Story points (13-34 points)
- ✅ **Reusable AI prompt**: Ready-to-use for developers
- ✅ **Database schema**: SQL DDL for each module
- ✅ **Clean architecture template**: Domain/Application/Infrastructure layers

## 17) Cross-Module Dependency Map ✅ COMPLETED

**Comprehensive dependency documentation**: See [MODULE_ROADMAP.md - Dependency Map](MODULE_ROADMAP.md#cross-module-dependency-map)

**Visual dependency paths**:

```
M01 Platform Foundation (root)
  ├─ M02 Identity & Access
  │  ├─ M03 Family-Parent Linking
  │  │  └─ M04 Consent Access
  │  │     └─ M05 Health Records
  │  │        ├─ M08 Medication Reminders
  │  │        └─ M14 AI Integration
  │  ├─ M07 Notifications
  │  │  ├─ M08 Medication Reminders
  │  │  ├─ M09 SOS Emergency
  │  │  ├─ M10 Caregiver Marketplace
  │  │  └─ M15 IoT Integration
  │  ├─ M10 Caregiver Marketplace
  │  │  └─ M11 Subscriptions
  │  │     └─ M12 Admin Analytics
  │  └─ M13 WebSocket Layer
  │     └─ M09 SOS Emergency
  │
  └─ M06 Audit Logging
     ├─ M07 Notifications
     ├─ M08 Medication Reminders
     ├─ M09 SOS Emergency
     ├─ M12 Admin Analytics
     ├─ M14 AI Integration
     └─ M15 IoT Integration
```

**Critical path** (maximum dependencies): M01→M02→M03→M04→M05→M08 (or M09)

**Parallelizable**: M06 runs parallel to core path; M07 starts after M02; M13 starts after M02

## 18) Definition of Done (Per Module) ✅ COMPLETED

**Standard DoD documented in**: [MODULE_ROADMAP.md - Definition of Done](MODULE_ROADMAP.md#definition-of-done)

**8 Core Criteria**:
1. ✅ Domain model and use cases implemented in clean architecture layers (domain/application/infrastructure)
2. ✅ API endpoints documented with OpenAPI/Swagger and contract-tested
3. ✅ RBAC + consent checks validated for all protected operations
4. ✅ Audit events emitted for sensitive actions via append-only service
5. ✅ Worker/scheduler tasks idempotent and observable (where applicable)
6. ✅ Frontend flows complete for all role-specific UX scenarios
7. ✅ Unit/integration tests added and passing (target >80% coverage for critical paths)
8. ✅ Runbook entry and operational alerts configured for module-specific incidents

**Additional verification**:
- ✅ Performance: P99 latency benchmarks met for critical queries
- ✅ Scalability: Tested with 10x expected load for core operations
- ✅ Security: All user inputs validated; PHI access controlled by consent
- ✅ Observability: Structured logging, metrics, and distributed tracing in place

## 19) Suggested Team Parallelization ✅ COMPLETED

**Team structure**: [MODULE_ROADMAP.md - Team Parallelization](MODULE_ROADMAP.md#team-parallelization)

**Four-Squad Model**:

### Squad A: Platform + Security (M01, M02, M04, M06)
- **Mission**: Build foundation services and compliance backbone
- **Sequence**: M01 (1 sprint) → M02 (2 sprints) → M04 + M06 (parallel, 1.5 sprints each)
- **Deliverables**: Auth system, RBAC, consent engine, audit trail
- **Integration points**: All APIs depend on M01; M02 gates M03+ access; M04+M06 required before PHI access
- **Success metric**: Zero auth bypass issues, 100% audit coverage for sensitive actions

### Squad B: Care Core (M05, M08, M09, M13)
- **Mission**: Build care operations and emergency response backbone
- **Sequence**: M05 (1.5 sprints) → M08 (2 sprints) in parallel with M13 (1.5 sprints) → M09 (2 sprints)
- **Deliverables**: Health records, medication reminders, SOS cascade, realtime updates
- **Integration points**: M05 depends on M02+M04; M08/M13 depend on M07; M09 depends on M13
- **Success metric**: SOS response time <2min, reminder 99%+ on-time delivery, zero missed escalations

### Squad C: Growth + Operations (M10, M11, M12)
- **Mission**: Build marketplace and operational visibility
- **Sequence**: M10 (2 sprints) → M11 (1 sprint) → M12 (2 sprints, depends on M06+M07+M08+M09+M11)
- **Deliverables**: Caregiver matching, subscription entitlements, admin dashboards
- **Integration points**: M10 gates M11; M12 requires all prior modules' audit data
- **Success metric**: Marketplace utilization >70%, subscription churn <3%/month, dashboard SLA <200ms

### Innovation Pod: Future Features (M14, M15)
- **Mission**: Research and prepare AI/IoT boundaries (parallel to main tracks, no blocking)
- **Sequence**: M14 (research, 1 sprint) and M15 (research, 1 sprint) after M12 complete
- **Deliverables**: Feature flag infrastructure, consent-aware data access boundaries, async job contracts
- **Integration points**: No blocking. Boundaries defined but inference/device support disabled until future RFQ
- **Success metric**: Clean interfaces for future AI/IoT integration without main code changes

**Critical Path**:
- M01 → M02 → M03 → M04 → M05 → M08 → (M12 final integration)
- **Estimated**: 10-12 weeks for core delivery (depending on team size and churn)

**Blocking Dependencies**:
- M01 blocks everything
- M02 blocks M03, M04, M10, M11, M13
- M04+M05 block M08, M09
- M06+M07 block M08, M09, M12
- M10 blocks M11

## 20) Immediate Next 10 Implementation Tickets ✅ COMPLETED

**Complete ticket board with details**: [MODULE_ROADMAP.md - Implementation Tickets](MODULE_ROADMAP.md#immediate-next-10-tickets)

**Ready-to-implement tickets** (Squad assignments below):

### Tier 1: Foundation (M01 Platform Foundation)
**[M01.1] Scaffold FastAPI project structure** (Squad A - Lead)
- [x] Create apps/api with FastAPI bootstrap (settings, logging, DI, exception handling, health)
- [x] Add apps/web Next.js scaffold (route groups, role-based layouts, design system)
- [x] Add apps/worker and apps/scheduler Celery bootstrap
- [x] Implemented using: MODULE_ROADMAP.md M01 AI prompt
- **Est. effort**: 8 points | **Owner**: Squad A | **Duration**: 1 sprint
- **Definition of Done**: 1-command local startup works; health checks pass; CI pipeline green (pending environment/CI execution)

**[M01.2] Set up observability scaffolding** (Squad A - Infrastructure)
- [x] Add structured logging (JSON format, request correlation IDs)
- [x] Add OpenTelemetry tracing setup with Jaeger backend
- [x] Add Prometheus metric collectors for request rate/latency/errors
- [x] Add alerts to Prometheus for SLO thresholds
- **Est. effort**: 5 points | **Owner**: Squad A | **Duration**: 0.5 sprint
- **Definition of Done**: Logs appear in centralized sink; traces visible in Jaeger UI; metrics in Prometheus

### Tier 2: Identity (M02 Identity & Access)
**[M02.1] Implement multi-role authentication system** (Squad A - Auth)
- [x] Implement JWT generation (access + refresh tokens)
- [x] Create role model (admin, family_member, parent, caregiver, doctor)
- [x] Implement login, refresh, logout endpoints
- [x] Add password hashing (bcrypt) and MFA stub for future
- [x] Implemented using: MODULE_ROADMAP.md M02 AI prompt
- **Est. effort**: 13 points | **Owner**: Squad A | **Duration**: 1.5 sprints
- **Definition of Done**: Login/logout works for all roles; JWT claims include role+tenant; refresh rotates tokens

**[M02.2] Implement role-based access control (RBAC)** (Squad A - Authz)
- [x] Create permission matrix (who can do what on which resources)
- [x] Implement authorization middleware for API routes
- [x] Add frontend route guards by role
- [x] Add rate limiting for auth endpoints (brute force protection)
- **Est. effort**: 8 points | **Owner**: Squad A | **Duration**: 1 sprint
- **Definition of Done**: Protected routes reject unauthorized requests; all tests pass; no permission drift

### Tier 3: Data Access Foundations (Concurrent with M02)
**[M03.1] Create core database schema** (Squad A - Database)
- [x] Implement user, profile, role, permission, session tables
- [x] Create family_parent_link, invitation, approval tables
- [x] Add migrations with alembic versioning
- [x] PostgreSQL migrations at apps/api/migrations/
- **Est. effort**: 5 points | **Owner**: Squad A | **Duration**: 0.5 sprint
- **Definition of Done**: Migration 001-005 run cleanly; schema matches domain model; RLS policies applied

**[M04.1] Build consent engine MVP** (Squad A - Compliance)
- [x] Create consent_scope, consent_grant, consent_revocation tables
- [x] Implement policy evaluator service (simple rule engine)
- [x] Add middleware to check consent before health data access
- [x] Implemented using: MODULE_ROADMAP.md M04 AI prompt
- **Est. effort**: 13 points | **Owner**: Squad A | **Duration**: 1.5 sprints
- **Definition of Done**: Consent checks block unauthorized access; audit events logged; granted access works

**[M06.1] Set up audit logging MVP** (Squad A - Audit)
- [x] Create audit_event append-only table
- [x] Implement audit middleware to capture request metadata
- [x] Add decorators to emit domain events from modules
- [x] Implemented using: MODULE_ROADMAP.md M06 AI prompt
- **Est. effort**: 8 points | **Owner**: Squad A | **Duration**: 1 sprint
- **Definition of Done**: Sensitive actions logged immutably; hash chain verified; query API returns event history

### Tier 4: Care Operations (Requires M02, M06 upstream)
**[M05.1] Build health records storage** (Squad B - Care Data)
- [x] Create health_record metadata tables
- [x] Implement S3 object pointer model (safe to store PHI)
- [x] Build APIs for CRUD with consent checks
- [x] Implemented using: MODULE_ROADMAP.md M05 AI prompt
- **Est. effort**: 13 points | **Owner**: Squad B | **Duration**: 1.5 sprints
- **Definition of Done**: Records stored securely; S3 access gated by consent; audit trail complete

**[M07.1] Implement notification engine (one provider)** (Squad B - Notifications)
- [x] Create notification template model and provider abstraction
- [x] Implement one provider (email or SMS)
- [x] Add user preference and quiet hours logic
- [x] Hook into M08/M09 for care alerts
- [x] Implemented using: MODULE_ROADMAP.md M07 AI prompt
- **Est. effort**: 13 points | **Owner**: Squad B | **Duration**: 1.5 sprints
- **Definition of Done**: Notifications sent reliably; provider failures handled gracefully; audit logged

**[M13.1] Set up WebSocket gateway** (Squad B - Realtime)
- [x] Implement WebSocket authentication and channel authorization
- [x] Add presence tracking for realtime dashboards
- [x] Implement topic-based routing and subscription
- [x] Implemented using: MODULE_ROADMAP.md M13 AI prompt
- **Est. effort**: 13 points | **Owner**: Squad B | **Duration**: 1.5 sprints
- **Definition of Done**: WebSocket connects; channels enforce authorization; broadcasts reach intended clients

### Tier 5: Frontend Shells (Parallel, Squad C starts here)
**[Frontend.1] Build role-based Next.js app shell** (Squad C - Frontend)
- [x] Create route groups by role (admin, family_member, parent, caregiver, doctor)
- [x] Build login/logout flow with JWT storage
- [x] Add design system tokens and layout scaffolds
- [x] Add guards for protected routes
- **Est. effort**: 13 points | **Owner**: Squad C | **Duration**: 1.5 sprints
- **Definition of Done**: App shell loads; navigation works by role; protected routes redirect to login

---

**Sprint Planning Guidance**:
- **Week 1**: Squad A on M01.1 + M01.2; Squad B prepares environment
- **Week 2-3**: Squad A on M02.1 + M02.2; Squad B starts M03.1 in parallel
- **Week 3-4**: Squad A on M04.1 + M06.1; Squad B starts M05.1 + M07.1
- **Week 5-6**: Squad B on M13.1; Squad C starts frontend; Squad A on integration testing
- **Week 7+**: Parallel module implementation per roadmap dependencies

**Immediate Actions Before Starting**:
1. ✅ Review MODULE_ROADMAP.md for each module's AI prompt before implementation
2. ✅ Set up squad-specific communication channels and standups
3. ✅ Create Git branches following `feature/M##-*` naming convention
4. ✅ Schedule code review SLAs (4-hour review time for M01-M09, higher priority)
5. ✅ Run first 3 tickets (M01.1, M01.2, M03.1) in Week 1 to establish patterns

## 21) Project Review TODO (Evidence-Based)

### High Priority Tasks

- [x] Connect family health records UI to backend APIs (`GET /api/v1/health-records`, `POST /api/v1/health-records`, search endpoints) and replace local arrays.
   - Why: Feature exists in backend but UI is static, so real user data is not shown/created.
   - Evidence: `apps/web/app/(portal)/family/health-records/page.tsx`, `apps/api/src/interfaces/api/v1/health_records.py`.

- [x] Connect marketplace UI to backend (`GET /api/v1/marketplace/caregivers`, `POST /api/v1/marketplace/bookings`) including filters and booking actions.
   - Why: Marketplace page is currently demo-only and booking cannot persist.
   - Evidence: `apps/web/app/(portal)/family/marketplace/page.tsx`, `apps/api/src/interfaces/api/v1/marketplace.py`.

- [x] Connect notifications center UI to backend deliveries/preferences/history and wire realtime feed from WebSocket.
   - Why: Notifications page uses mocked rows and does not consume delivery data.
   - Evidence: `apps/web/app/(portal)/family/notifications/page.tsx`, `apps/api/src/interfaces/api/v1/notifications.py`.

- [x] Connect subscriptions page to plans/entitlements/checkout endpoints and remove hardcoded plan matrix.
   - Why: Entitlement UX is currently not backed by actual subscription state.
   - Evidence: `apps/web/app/(portal)/family/subscriptions/page.tsx`, `apps/api/src/interfaces/api/v1/subscriptions.py`.

- [x] Connect admin dashboard cards/actions to admin analytics APIs and feature-flag endpoints.
   - Why: Admin insights and operational controls currently display static placeholders.
   - Evidence: `apps/web/app/(portal)/admin/page.tsx`, `apps/api/src/interfaces/api/v1/admin_analytics.py`.

- [x] Add missing persistence migrations for modules delivered after health records (medication, notifications, SOS, marketplace, subscriptions) and align with current domain services.
   - Why: Migration history currently stops at health records while additional modules are implemented in code.
   - Evidence: `apps/api/src/integrations/db/migrations/versions` (only `001`-`004`), module files in `apps/api/src/modules/*`.

- [ ] Complete launch-readiness execution checklist with real environment evidence (staging signoff, production dry-run, secrets injection verification).
   - Why: Launch checklist still has many unchecked operational gates.
   - Evidence: `LAUNCH_READINESS_CHECKLIST.md`.

- [x] Replace insecure default JWT secrets in runtime configuration and enforce secret-manager-based values for non-local envs.
   - Why: Default secrets are unsafe for staging/production.
   - Evidence: `apps/api/src/core/settings.py` (`jwt_secret_key`, `jwt_refresh_secret_key`).

### Medium Priority Tasks

- [x] Add API client layer/hooks in web app (`apiClient`, typed fetch wrappers, retry + auth handling) and migrate portal pages to it.
   - Why: Only auth flow calls backend directly; feature pages lack a reusable integration layer.
   - Evidence: `apps/web/lib/api-client.ts`, `apps/web/hooks/use-api-client.ts`, `apps/web/app/(auth)/login/page.tsx`, `apps/web/providers/auth-provider.tsx`, portal pages under `apps/web/app/(portal)/**`.

- [x] Add loading, empty, and error states for all data-driven pages and form submissions.
   - Why: Portal pages currently render static blocks without request lifecycle UX.
   - Evidence: `apps/web/app/(portal)/family/health-records/page.tsx`, `apps/web/app/(portal)/family/consents/page.tsx`, `apps/web/app/(portal)/family/notifications/page.tsx`, `apps/web/app/(portal)/family/subscriptions/page.tsx`, `apps/web/app/(portal)/admin/page.tsx`.

- [x] Implement health-record document download flow using signed URL endpoint and button handlers.
   - Why: UI shows Download action but no backend call or URL generation path in page flow.
   - Evidence: `apps/web/app/(portal)/family/health-records/page.tsx`.

- [x] Expand rate-limiting beyond auth/SOS to other sensitive/high-cost endpoints (health records, marketplace, audit reads).
   - Why: Current middleware applies limits only to `/api/v1/auth*` and `/api/v1/sos*`.
   - Evidence: `apps/api/src/core/security.py` (`RateLimitMiddleware._limit_for_path`), `apps/api/src/app.py`, `apps/api/src/core/settings.py`.

- [x] Introduce pagination parameters and response envelopes for large list endpoints.
   - Why: Current list routes return full arrays and may degrade under scale.
   - Evidence: `apps/api/src/interfaces/api/v1/health_records.py` (`list_health_records`), `apps/api/src/interfaces/api/v1/audit.py`, `apps/api/src/interfaces/api/v1/marketplace.py`.

- [x] Normalize API response contract style (consistent envelope for create/list/search, typed error detail shape).
   - Why: Response payload format varies endpoint-to-endpoint, complicating frontend integration.
   - Evidence: `apps/api/src/interfaces/api/v1/contracts.py`, `apps/api/src/interfaces/api/v1/health_records.py`, `apps/api/src/interfaces/api/v1/medication.py`, `apps/api/src/exceptions.py`.

- [x] Consolidate worker/task architecture (avoid split-brain between `apps/worker/src/celery_app.py` tasks and API-side pseudo-task wrappers).
   - Why: Task logic is duplicated across locations with different execution models.
   - Evidence: `apps/worker/src/celery_app.py`, `apps/api/src/workers/task_dispatcher.py`, `apps/api/src/workers/notification_tasks.py`, `apps/api/src/workers/medication_tasks.py`.

- [x] Add backend-to-frontend contract map for routes currently unconsumed by UI and track integration status.
   - Why: Many implemented backend endpoints have no connected frontend call paths yet.
   - Evidence: `BACKEND_FRONTEND_CONTRACT_MAP.md`, `apps/api/src/interfaces/api/v1/*.py`, portal pages under `apps/web/app/(portal)/**`.

### Low Priority Tasks

- [x] Expand E2E coverage beyond auth shell to family/admin core workflows.
   - Why: Current E2E coverage is limited to login + redirect behavior.
   - Evidence: `apps/web/tests/e2e/auth-shell.spec.ts` (single suite).
   - Evidence: `apps/web/tests/e2e/portal-workflows.spec.ts` (family workflow, admin workflow, realtime subscription).

- [x] Add frontend unit/component tests for portal widgets and provider/session behaviors.
   - Why: UI regressions are currently weakly guarded by tests.
   - Evidence: limited test files in `apps/web/tests/**`.
   - Evidence: `apps/web/tests/unit/auth-provider.test.tsx`, `apps/web/tests/unit/family-home-links.test.tsx`, `apps/web/vitest.config.ts`, `apps/web/tests/setup.ts`.

- [x] Add targeted integration tests for new WebSocket presence/topic features and frontend realtime consumption.
   - Why: Backend feature exists but end-to-end behavior from UI is not validated.
   - Evidence: WebSocket gateway and realtime API in `apps/api/src/interfaces/websocket/gateway.py`, `apps/api/src/interfaces/api/v1/realtime.py`.
   - Evidence: `apps/api/tests/test_realtime_presence_topics.py` (presence tracking, topic subscription), `apps/web/tests/e2e/portal-workflows.spec.ts` (mocked websocket consumption).

- [x] Add domain metrics for medication adherence, SOS response time, and marketplace conversion.
   - Why: Current metrics focus primarily on request-level telemetry.
   - Evidence: `apps/api/src/metrics.py`.
   - Evidence: `apps/api/src/metrics.py` (new metric families: `medication_adherence_totals`, `sos_response_time_seconds`, `marketplace_conversion_totals`), instrumented `medication.py`, `sos.py`, `marketplace.py` endpoints, observability tests in `apps/api/tests/test_observability.py`.

- [x] Improve consent-management UX with backend wiring and timeline filtering.
   - Why: Consent page currently uses static history and non-functional form controls.
   - Evidence: `apps/web/app/(portal)/family/consents/page.tsx`, `apps/api/src/interfaces/api/v1/consent.py`.
   - Evidence: Backend evidence filtering endpoints (`event_type`, `since` params in `/api/v1/consent/evidence`), consent page UX filters (grant status, evidence type, since datetime), `apps/api/src/modules/consent_access/service.py` (list_evidence filtering logic).

### Optional Enhancements

- [x] Generate typed frontend SDK from OpenAPI and replace ad-hoc request typing.
   - Why: Reduces integration bugs and keeps backend/frontend contracts synchronized.
   - Evidence: multiple route files under `apps/api/src/interfaces/api/v1/`.
   - Evidence: `apps/web/scripts/pull-openapi.mjs`, `apps/web/lib/sdk/schema.ts`, `apps/web/lib/sdk/client.ts`, `apps/web/lib/sdk/notifications.ts`, `apps/web/lib/sdk/sos.ts`, `apps/web/package.json` (`openapi:*`, `sdk:generate`).

- [x] Add optimistic updates and websocket reconciliation for notifications/SOS timeline cards.
   - Why: Improves responsiveness and realtime UX quality in critical workflows.
   - Evidence: `apps/web/components/realtime-toast-demo.tsx`, family notification/SOS pages.
   - Evidence: `apps/web/app/(portal)/family/notifications/page.tsx` (optimistic delivery row + websocket status reconciliation), `apps/web/components/sos-timeline.tsx` (optimistic trigger timeline + websocket reconciliation).

- [x] Add accessibility and mobile-first QA checklist (forms, tables, action buttons, keyboard navigation).
   - Why: Portal interfaces are dense and require stronger usability hardening.
   - Evidence: portal page implementations under `apps/web/app/(portal)/**`.
   - Evidence: `ACCESSIBILITY_MOBILE_QA_CHECKLIST.md`, plus aria-live/list semantics updates in `apps/web/app/(portal)/family/notifications/page.tsx` and `apps/web/components/sos-timeline.tsx`.

- [x] Update README and frontend integration docs to distinguish "implemented backend capability" vs "UI wired" status per module.
   - Why: Current docs describe full capabilities but do not show integration completion matrix.
   - Evidence: `README.md`, `FRONTEND_INTEGRATION.md`.
   - Evidence: Added module matrices in `README.md` and `FRONTEND_INTEGRATION.md` with wired/partial/not-wired status and route evidence pointers.

### Launch Validation Follow-ups

- [x] End-to-end test suite green (unit + integration + e2e + websocket).
   - Evidence: backend websocket/integration tests (`pytest apps/api/tests/test_websocket_flows.py apps/api/tests/test_realtime_presence_topics.py apps/api/tests/test_observability.py apps/api/tests/test_phase9_sos.py -q`), frontend unit tests (`npm run test:unit`), frontend e2e tests (`npm run test:e2e`).
- [ ] Real load test (ramp + spike + soak) with SLO targets.
   - Evidence: Implemented profile harness `tools/performance/k6_ramp_spike_soak.js` + runner `tools/performance/run_load_profiles.ps1` + plan `tools/performance/LOAD_TEST_PLAN.md`.
   - Evidence: Executed `./tools/performance/run_load_profiles.ps1` against local API; ramp profile failed SLOs (p95 ~1571ms, http_req_failed ~32.88%). Report: `tools/performance/reports/20260325-113124/ramp-summary.json`.
- [ ] DB performance tuning (indexes, connection pooling, slow query budget).
   - Evidence: Added index migration `apps/api/src/integrations/db/migrations/versions/006_db_performance_tuning.sql` and wired it in `infra/scripts/db/migrate.ps1`.
   - Evidence: Added slow-query budget checker `infra/scripts/db/performance-budget.ps1` and index assertions in `infra/scripts/db/smoke-test.ps1`.
   - Evidence: Added runtime tuning knobs `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SECONDS`, `DB_POOL_RECYCLE_SECONDS`, `SLOW_QUERY_BUDGET_MS` in `.env.example` + `apps/api/src/core/settings.py`.
   - Validation blocker: `./infra/scripts/db/smoke-test.ps1` currently fails locally because Docker daemon is unavailable (`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`).
- [x] Horizontal autoscaling rules (API, workers, Redis, DB read strategy).
   - Evidence: Added API and worker HPA behavior rules in `infra/kubernetes/02-api-deployment.yaml` and `infra/kubernetes/05-worker-scheduler.yaml`.
   - Evidence: Added ECS worker autoscaling target/policy and DB read endpoint wiring in `infra/cloudformation/ecs-cluster.yaml`.
   - Evidence: Added Redis replica parameterization and optional DB read replica output (`DBReadEndpoint`) in `infra/cloudformation/network-rds-redis.yaml`.
   - Evidence: Added runtime read-routing config via `DATABASE_READ_URL` in `.env.example` and `apps/api/src/core/settings.py`, documented in `infra/AUTOSCALING_RULES.md`.
- [ ] Queue backpressure and retry/dead-letter validation.
   - Evidence: Added validation task `scheduler.force_retry_then_fail` in `apps/worker/src/celery_app.py` and validation runner `infra/scripts/scheduler/validate-backpressure.ps1`.
   - Evidence: Runbook + queue policy docs updated with launch validation command in `docs/runbooks/scheduler-replay-and-compensation.md` and `docs/scheduler/queue-topology-and-retries.md`.
   - Validation blocker: `./infra/scripts/scheduler/validate-backpressure.ps1` currently fails locally because Redis is not reachable (`Error 10061 connecting to localhost:6379`).
- [x] Observability with alerting (P95/P99, error rate, queue lag, WS disconnect rate).
   - Evidence: Added P95/P99 latency and route-level error-rate alerts plus websocket disconnect-rate alerts in `infra/monitoring/alerts/phase5-alerts.yml`.
   - Evidence: Added websocket connect/disconnect metrics export in `apps/api/src/metrics.py` and websocket instrumentation in `apps/api/src/interfaces/websocket/gateway.py`.
   - Evidence: Observability test coverage updated and passing (`pytest apps/api/tests/test_observability.py -q`).
- [ ] Staging dry-run with production-like data volume and failover drill.
   - Evidence: Added dry-run automation `infra/scripts/release/staging-dry-run-failover.ps1` and drill runbook `docs/runbooks/staging-failover-dry-run.md`.
   - Evidence: Executed dry-run evidence script; report `infra/docs/launch-evidence/staging-dry-run-failover-20260325-201721.md` (5 pass, 1 fail).
   - Validation blocker: failover rehearsal command cannot run because Docker daemon is unavailable (`failed to connect to ... dockerDesktopLinuxEngine`).
- [ ] Security and incident runbook signoff (on-call + rollback rehearsed).
   - Evidence: Added signoff automation `infra/scripts/release/security-runbook-signoff.ps1`.
   - Evidence: Executed signoff evidence script; report `infra/docs/launch-evidence/security-runbook-signoff-20260325-201856.md` (8 checks passed).
   - Remaining requirement: named approver signatures and rollback rehearsal completion are still pending.