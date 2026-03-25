**SPRINT PROGRESS UPDATE: M05.1, M07.1, M08.1 COMPLETE ✅**

  Latest delivery summary:
  - M05.1: Health records storage with consent checks and S3 abstraction
  - M07.1: Notifications provider layer (email/SMS), preferences, worker tasks, API coverage
  - M08.1: Medication scheduling cadence + adherence tracking (taken/skipped/missed)
  - Full API suite: 86 tests passing, 1 warning, 0 regressions

**Next Task**: Start M09.1 - SOS emergency cascade hardening and escalation workflows
# 🚀 Eldercare Platform: Sprint-wise Implementation Tasks

**Current Phase**: M01-M04 Implementation (Week 1-4)  
**Team Size**: 1 (Initially solo, expandable)  
**Total Duration**: 12+ weeks for full platform

---

## 📅 SPRINT 1: Week 1 — Platform Foundation (M01)

### Daily Breakdown

#### 🔷 Day 1-2: M01.1 - FastAPI Scaffold (8 points)

**What to Do**:
- [x] Create directory structure: `apps/api/src/` with subdirectories
  ```
  apps/api/
  ├── src/
  │   ├── __init__.py
  │   ├── config.py          (Settings management)
  │   ├── app.py             (FastAPI factory)
  │   ├── di.py              (Dependency injection)
  │   ├── logging_config.py  (Structured logging)
  │   ├── exceptions.py      (Global error handlers)
  │   ├── health.py          (Health checks)
  │   └── main.py            (Entry point)
  └── tests/
      └── test_bootstrap.py  (Bootstrap tests)
  ```

- [x] Create `src/config.py` with Pydantic Settings
- [x] Create `src/app.py` with FastAPI factory function
- [x] Create `src/di.py` with dependency injection container
- [x] Create `src/logging_config.py` with JSON logging + correlation IDs
- [x] Create `src/exceptions.py` with global exception handlers
- [x] Create `src/health.py` with `/health` and `/ready` endpoints
- [x] Create `tests/test_bootstrap.py` with app startup tests

**Expected Output**: API boots in < 2 seconds, health check responds < 100ms

**Related Docs**: See MODULE_ROADMAP.md → M01 → "Reusable AI Developer Prompt"

**Command to Give Me**: 
```
Start M01.1 - FastAPI scaffold
```

---

#### 🔷 Day 3: M01.2 - Observability Setup (5 points)

**What to Do**:
- [x] Add `logging_config.py` JSON formatter
  - Structured logs with timestamp, level, correlation_id, message
- [x] Add `OpenTelemetry` tracing imports
- [x] Create `src/tracing.py` with Jaeger configuration
- [x] Add Prometheus metrics collectors to `src/metrics.py`
  - Request count, latency (p50/p95/p99), error rate
- [x] Update `app.py` to include metrics middleware
- [x] Create `tests/test_observability.py` with metric collection tests

**Expected Output**: 
- Logs appear as JSON in stdout
- Prometheus metrics at `GET /metrics`
- Traces visible in local Jaeger (if running)

**Command to Give Me**: 
```
Start M01.2 - Observability and metrics
```

---

### ✅ Sprint 1 Success Criteria

- [x] API starts without errors
- [x] Health check responds within 100ms
- [x] All logs are JSON formatted
- [x] Metrics endpoint returns Prometheus format
- [x] DI container resolves dependencies
- [x] Tests pass (pytest > 80% coverage)

---

## 📅 SPRINT 2: Week 2 — Identity & Access (M02)

### Daily Breakdown

#### 🔷 Day 4-5: M02.1 - Authentication System (13 points)

**What to Do**:
- [x] Create `src/modules/identity/` directory structure
  ```
  src/modules/identity/
  ├── domain/
  │   ├── __init__.py
  │   └── models.py        (User, Role, Permission entities)
  ├── application/
  │   ├── __init__.py
  │   └── services.py      (AuthenticationService, PasswordService)
  ├── infrastructure/
  │   ├── __init__.py
  │   └── repositories.py  (UserRepository, SessionRepository)
  └── tests/
      └── test_auth.py
  ```

- [x] Create database migrations for `users`, `roles`, `permissions`, `refresh_tokens` tables
- [x] Implement `models.py` with User aggregate, Role enum, PasswordHash value object
- [x] Implement `services.py` with:
  - `AuthenticationService.login(email, password) → tokens`
  - `AuthenticationService.refresh(refresh_token) → new_access_token`
  - `AuthenticationService.logout(user_id)`
  - `PasswordService.hash_password()` and `verify_password()`
- [x] Create JWT token generation/validation utilities
- [x] Create API endpoints:
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/refresh`
  - `POST /api/v1/auth/logout`
- [-] Add bcrypt for password hashing (fallback to pbkdf2 in current environment due bcrypt backend issue)
- [x] Create tests for valid/invalid credentials

**Expected Output**: 
- Login with valid credentials returns access + refresh tokens
- Refresh token rotates access token
- Invalid credentials rejected

**Related Docs**: See MODULE_ROADMAP.md → M02 → Models & Prompts

**Command to Give Me**: 
```
Start M02.1 - Authentication endpoints (login/refresh/logout)
```

---

#### 🔷 Day 6: M02.2 - RBAC & Authorization (8 points)

**What to Do**:
- [x] Create database migrations for role assignments
- [x] Add role enum: `admin`, `family_member`, `parent`, `caregiver`, `doctor`
- [x] Create `src/middleware/auth.py` with:
  - JWT token validator
  - Current user extractor
  - `@require_auth` decorator
  - `@require_role("admin")` decorator
- [x] Create protected route examples:
  - `GET /api/v1/users/me` (authenticated users only)
  - `GET /api/v1/admin/users` (admin only)
- [x] Add rate limiting to auth endpoints (brute force protection)
- [x] Create tests for authorized/unauthorized access

**Expected Output**: 
- Protected routes reject requests without token
- Non-admin requests to `/admin/*` rejected
- Valid token with proper role grants access

**Command to Give Me**: 
```
Start M02.2 - RBAC middleware and role guards
```

---

### ✅ Sprint 2 Success Criteria

- [x] All roles can login
- [x] JWT tokens validate correctly
- [x] Refresh tokens rotate access tokens
- [x] Admin routes reject non-admin users
- [x] Password stored hashed, never plain text
- [ ] Tests cover auth flows (90%+ coverage)
- [x] Auth latency < 50ms

---

## 📅 SPRINT 3: Week 3 — Data Foundation (M03, M04, M06)

### Daily Breakdown

#### 🔷 Day 7: M03.1 - Database Schema & Family Linking (5 points)

**What to Do**:
- [x] Create migration for core tables:
  - `users`, `roles`, `permissions`
  - `family_links` (relationships)
  - `invitations` (7-day expiry)
- [x] Add unique constraints and indexes for performance
- [x] Create `src/modules/family/domain/models.py`:
  - `FamilyLink` aggregate with status (invited, accepted, rejected)
  - `RelationshipType` enum
  - `Invitation` value object with expiry
- [x] Create `src/modules/family/application/services.py`:
  - `FamilyLinkService.send_invitation(email, relationship_type)`
  - `FamilyLinkService.accept_invitation(invite_id)`
  - `FamilyLinkService.unlink(link_id)`

**Expected Output**: Database migrations run cleanly, schema matches diagrams

**Related Docs**: See MODULE_ROADMAP.md → M03 → Database Schema Section

**Command to Give Me**: 
```
Start M03.1 - Database schema and family linking domain
```

---

#### 🔷 Day 8: M04.1 - Consent Engine MVP (13 points)

**What to Do**:
- [x] Create `src/modules/consent/` directory structure
- [x] Create `src/modules/consent/domain/models.py`:
  - `ConsentGrant` aggregate (grantor, grantee, scopes, valid_from, valid_to)
  - `Scope` enum: `medical_history`, `medications`, `appointments`, `vitals`
  - `ConsentDecision` value object (allow/deny/reason)
- [x] Create `src/modules/consent/application/services.py`:
  - `ConsentService.grant_access(grantor_id, grantee_id, scopes, valid_to)`
  - `ConsentService.revoke_access(grant_id)`
  - `ConsentService.can_access(user_id, resource_id, scope) → bool`
- [x] Create `src/middleware/consent.py`:
  - Decorator `@require_consent("medical_history")` for protected endpoints
- [x] Create API endpoints:
  - `POST /api/v1/consent/grant`
  - `POST /api/v1/consent/grant/{id}/revoke`
  - `GET /api/v1/consent/grants/mine`
- [x] Add Redis caching for policy decisions (5-min TTL)

**Expected Output**: 
- Consent grants stored correctly
- Policy evaluation cached (< 10ms)
- Revocation takes effect within 1 second

**Related Docs**: See MODULE_ROADMAP.md → M04 → Policy Evaluator

**Command to Give Me**: 
```
Start M04.1 - Consent engine (grant/revoke/check_access)
```

---

#### 🔷 Day 9: M06.1 - Audit Logging MVP (8 points)

**What to Do**:
- [x] Create `src/modules/audit/` directory structure
- [x] Create `src/modules/audit/domain/models.py`:
  - `AuditEvent` aggregate (user_id, action, resource_type, resource_id, timestamp)
  - `Action` enum: CREATE, READ, UPDATE, DELETE, GRANT, REVOKE
- [x] Create database table: `audit_events` (append-only, never update/delete)
- [x] Create `src/middleware/audit.py`:
  - Middleware that logs all REST API calls (request/response)
  - Mask sensitive fields (passwords, tokens)
- [x] Create `src/modules/audit/application/services.py`:
  - `AuditService.log_event(user_id, action, resource_type, resource_id)`
- [x] Create query endpoint:
  - `GET /api/v1/audit/events?user_id=...&action=...`
- [x] Add tests

**Expected Output**: All API calls logged, audit trail immutable

**Command to Give Me**: 
```
Start M06.1 - Audit logging middleware (append-only)
```

---

### ✅ Sprint 3 Success Criteria

- [x] Family invitations working
- [x] Consent grants/revokes working
- [x] Audit middleware active on all routes
- [x] Policy decisions cached
- [x] All tests passing (90%+ coverage)

---

## 📅 SPRINT 4: Week 4 — Care Foundation (M05, M07)

### Daily Breakdown

#### 🔷 Day 10: M05.1 - Health Records Storage (13 points)

**What to Do**:
 [x] Create `src/modules/health/` directory structure
 [x] Create database table: `health_records` with JSONB `data` column
 [x] Create `src/modules/health/domain/models.py`:
  - `HealthRecord` aggregate (patient_id, created_by_id, record_type, data)
  - `RecordType` enum: medical_history, lab_results, vitals, prescription
  - `DocumentReference` value object (s3_key, file_hash, mime_type)
 [x] Create `src/modules/health/application/services.py`:
  - `HealthRecordService.create(patient_id, created_by_id, record_type, data)`
  - `HealthRecordService.get(record_id)` — applies consent checks
  - `HealthRecordService.search(patient_id, type, date_range)`
 [x] Create S3 abstraction in `infrastructure/s3_provider.py`
 [x] Create API endpoints:
  - `POST /api/v1/health/records` (create with optional file upload)
  - `GET /api/v1/health/records?type=...&date_from=...`
  - `GET /api/v1/health/records/{id}` (consent-checked)
 [x] Add M04 consent middleware to retrieval endpoints
 [x] Add tests (12 tests created: domain models, application service, S3 provider)

**Expected Output**: Health records stored securely, consent enforced on reads

**Command to Give Me**: 
```
Start M05.1 - Health records storage with S3
```

---

#### 🔷 Day 11-12: M07.1 - Notifications Provider (13 points)

**What to Do**:
- [x] Create `src/modules/notifications/` directory structure
- [x] Create `src/modules/notifications/infrastructure/providers/base.py`:
  - Abstract `BaseProvider` class with `send()` method
- [x] Implement `src/modules/notifications/infrastructure/providers/email.py`:
  - Email provider using SendGrid or SMTP
- [x] Implement `src/modules/notifications/infrastructure/providers/sms.py`:
  - SMS provider stub (Twilio integration for later)
- [x] Create `src/modules/notifications/domain/models.py`:
  - `Notification` aggregate (recipient_id, type, status, channels)
  - `NotificationStatus` enum: pending, sent, delivered, failed
- [x] Create `src/modules/notifications/application/services.py`:
  - `NotificationService.send(recipient_id, type, data)`
- [x] Create Celery tasks: `send_email`, `send_sms` in `src/workers/notification_tasks.py`
- [x] Create API: `POST /api/v1/notifications/send` (internal)
- [x] Add user preference endpoint: `PUT /api/v1/notifications/preferences`
- [x] Tests for template rendering, provider failures

**Expected Output**: 
- Email notifications send correctly
- Preferences respected (opt-in/out)
- Failures logged, retried with backoff

**Command to Give Me**: 
```
Start M07.1 - Notifications engine with email + SMS providers
```

---

### ✅ Sprint 4 Success Criteria

- [x] Health records stored + retrieved (consent-checked)
- [x] Email notifications send
- [x] User preferences work
- [x] Celery tasks execute
- [ ] All modules (M05, M07) have >80% test coverage

---

## 📅 SPRINT 5: Week 5 — Frontend Scaffold

#### 🔷 Day 13-14: Frontend Shell (13 points)

**What to Do**:
- [x] Create `apps/web/` Next.js scaffold (already done? confirm)
- [x] Create route groups by role:
  - `(admin)/*` — admin-only pages
  - `(family_member)/*` — family member pages
  - `(parent)/*` — parent pages
- [x] Build login page with JWT storage
- [x] Build protected route middleware
- [x] Create design system tokens (colors, typography)
- [x] Build auth context provider
- [x] Create signout functionality
- [x] Add E2E tests (Playwright or Cypress)

**Expected Output**: Frontend app boots, login/logout works

**Command to Give Me**: 
```
Start Frontend - Next.js app shell with auth
```

---

## 📊 Summary: First 5 Sprints (10 Points each)

| Sprint | Week | Module | Points | Duration |
|--------|------|--------|--------|----------|
| 1 | W1 | M01 (Platform) | 13 | 5 days |
| 2 | W2 | M02 (Auth) | 21 | 5 days |
| 3 | W3 | M03, M04, M06 | 26 | 5 days |
| 4 | W4 | M05, M07 | 26 | 5 days |
| 5 | W5 | Frontend | 13 | 5 days |
| | | **TOTAL** | **99** | **4 weeks** |

---

## 🎯 How to Use This File

1. **Pick a sprint** above (start with Sprint 1 Day 1)
2. **Tell me the task**: 
   ```
   Start M01.1 - FastAPI scaffold
   ```
3. **I will**:
   - Create all files
   - Write complete code
   - Add tests
   - Update this file with ✅ when done
4. **You then move to next task**

---

## 📌 Prerequisites Before Starting

- [x] Python 3.11+ with venv activated
- [x] PostgreSQL running (docker-compose)
- [x] Redis running (docker-compose)
- [x] Docker daemon active (for S3 moto)
- [ ] All dependencies installed (`pip install -r requirements.txt`)

To check dependencies:
```bash
python --version              # Should be 3.11+
psql --version               # Should be installed
redis-cli ping              # Should respond PONG
```

---

## 🔥 Let's Get Started!

**Jo bhi task karna ho, seedha bolo**:

```
Start M01.1 - FastAPI scaffold
```

Main immediately:
- Create all files
- Write code
- Add tests
- Update this list with ✅

**Ready?** 🚀
