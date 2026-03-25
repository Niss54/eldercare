# Backend to Frontend Contract Map

Last updated: 2026-03-24

This document tracks API v1 route consumption status between backend routers and web clients.

Status legend:
- `Wired`: explicit frontend call exists
- `Partial`: module has some wired routes, others pending
- `Not Wired`: no active frontend call path found

## Module Status Summary

| Module | Integration Status | Notes |
|---|---|---|
| auth | Partial | login, logout, MFA challenge wired; refresh/me/reset flows pending |
| users | Not Wired | no active web consumption |
| health-records | Wired | list/create/search/download URL wired |
| consent | Partial | scopes, grants mine/create/revoke, evidence wired; request/review/renew pending |
| family-links | Not Wired | no active web consumption |
| medication | Not Wired | no active web consumption |
| marketplace | Partial | caregivers list + create booking wired; moderation/verification flows pending |
| notifications | Partial | deliveries, preferences, send wired; callbacks/templates pending |
| sos | Not Wired | no active web consumption |
| subscriptions | Partial | plans/me/entitlements/checkout wired; lifecycle and billing ops pending |
| admin-analytics | Wired | dashboard, actions, feature flags, export wired |
| audit | Not Wired | no active web consumption |
| realtime (REST) | Not Wired | websocket is used, REST realtime endpoints not consumed |

## Verified Wired Routes

| Method | Route | Consumed by |
|---|---|---|
| POST | /api/v1/auth/login | apps/web/app/(auth)/login/page.tsx |
| POST | /api/v1/auth/mfa/challenge | apps/web/app/(auth)/login/page.tsx |
| POST | /api/v1/auth/logout | apps/web/providers/auth-provider.tsx |
| GET | /api/v1/health-records | apps/web/app/(portal)/family/health-records/page.tsx |
| POST | /api/v1/health-records/ | apps/web/app/(portal)/family/health-records/page.tsx |
| GET | /api/v1/health-records/search/by-type | apps/web/app/(portal)/family/health-records/page.tsx |
| GET | /api/v1/health-records/search/by-date-range | apps/web/app/(portal)/family/health-records/page.tsx |
| GET | /api/v1/health-records/{record_id}/document-download-url | apps/web/app/(portal)/family/health-records/page.tsx |
| GET | /api/v1/consent/scopes | apps/web/app/(portal)/family/consents/page.tsx |
| GET | /api/v1/consent/grants/mine | apps/web/app/(portal)/family/consents/page.tsx |
| POST | /api/v1/consent/grants | apps/web/app/(portal)/family/consents/page.tsx |
| POST | /api/v1/consent/grant/{grant_id}/revoke | apps/web/app/(portal)/family/consents/page.tsx |
| GET | /api/v1/consent/evidence | apps/web/app/(portal)/family/consents/page.tsx |
| GET | /api/v1/marketplace/caregivers | apps/web/app/(portal)/family/marketplace/page.tsx |
| POST | /api/v1/marketplace/bookings | apps/web/app/(portal)/family/marketplace/page.tsx |
| GET | /api/v1/notifications/deliveries | apps/web/app/(portal)/family/notifications/page.tsx |
| GET | /api/v1/notifications/preferences/{user_id} | apps/web/app/(portal)/family/notifications/page.tsx |
| PUT | /api/v1/notifications/preferences/{user_id} | apps/web/app/(portal)/family/notifications/page.tsx |
| POST | /api/v1/notifications/send | apps/web/app/(portal)/family/notifications/page.tsx |
| GET | /api/v1/subscriptions/plans | apps/web/app/(portal)/family/subscriptions/page.tsx |
| GET | /api/v1/subscriptions/me | apps/web/app/(portal)/family/subscriptions/page.tsx |
| GET | /api/v1/subscriptions/entitlements | apps/web/app/(portal)/family/subscriptions/page.tsx |
| GET | /api/v1/subscriptions/entitlements/check | apps/web/app/(portal)/family/marketplace/page.tsx |
| POST | /api/v1/subscriptions/checkout | apps/web/app/(portal)/family/subscriptions/page.tsx |
| GET | /api/v1/admin-analytics/dashboard | apps/web/app/(portal)/admin/page.tsx |
| GET | /api/v1/admin-analytics/feature-flags | apps/web/app/(portal)/admin/page.tsx |
| POST | /api/v1/admin-analytics/feature-flags/{flag_key} | apps/web/app/(portal)/admin/page.tsx |
| POST | /api/v1/admin-analytics/actions/disable-account | apps/web/app/(portal)/admin/page.tsx |
| POST | /api/v1/admin-analytics/actions/resend-invite | apps/web/app/(portal)/admin/page.tsx |
| POST | /api/v1/admin-analytics/actions/incident-review | apps/web/app/(portal)/admin/page.tsx |
| GET | /api/v1/admin-analytics/reports/export | apps/web/app/(portal)/admin/page.tsx |

## High-Value Unconsumed Route Backlog

| Module | Method | Route |
|---|---|---|
| auth | POST | /api/v1/auth/refresh |
| auth | GET | /api/v1/auth/me |
| users | GET | /api/v1/users/me |
| family-links | GET | /api/v1/family-links/links/me |
| family-links | POST | /api/v1/family-links/requests |
| medication | POST | /api/v1/medication/schedules |
| medication | GET | /api/v1/medication/metrics |
| marketplace | POST | /api/v1/marketplace/caregivers/{caregiver_id}/verification-review |
| marketplace | GET | /api/v1/marketplace/incidents |
| sos | POST | /api/v1/sos/incidents/trigger |
| sos | GET | /api/v1/sos/incidents |
| subscriptions | POST | /api/v1/subscriptions/lifecycle/renew |
| subscriptions | GET | /api/v1/subscriptions/invoices |
| audit | GET | /api/v1/audit/events |
| audit | GET | /api/v1/audit/compliance/report |
| realtime | GET | /api/v1/realtime/events/{channel} |

## Notes

- WebSocket integration is active via `/ws/notifications`, but REST realtime routes under `/api/v1/realtime/*` are currently unused.
- Marketplace page still uses direct `fetch`; migration to shared API client remains a follow-up cleanup task.
