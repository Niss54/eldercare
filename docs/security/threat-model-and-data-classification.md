# Threat Model and Data Classification

## Data Classes
- PHI: health records, medication adherence, SOS incident medical context, consent evidence.
- PII: user profile names, emails, phone numbers, caregiver identity details.
- Operational: queue metrics, system logs without patient identifiers, deployment metadata.

## Primary Assets
- Identity tokens and refresh sessions.
- Consent grants and policy decisions.
- Health record metadata and object pointers.
- SOS incident timelines and responder acknowledgements.
- Audit event chain.

## Trust Boundaries
- Browser to web application.
- Web application to API.
- API to PostgreSQL/Redis/object storage.
- Internal services to third-party providers (SMS/email/payment).

## Key Threats (STRIDE)
- Spoofing: stolen JWT/refresh tokens, forged websocket clients.
- Tampering: unauthorized edits to PHI or audit logs.
- Repudiation: denial of sensitive actions without immutable audit evidence.
- Information disclosure: over-broad role access, consent bypass, object-store leaks.
- Denial of service: auth and SOS endpoint abuse, queue flooding.
- Elevation of privilege: permission drift, stale sessions, missing MFA.

## Mitigations Implemented
- RBAC permission checks and resource-level gates on sensitive routes.
- Consent policy enforcement in route checks and middleware for health record paths.
- JWT key IDs with key-ring decode support for rotation.
- Refresh token rotation and explicit revocation tracking.
- Mandatory MFA for admin and doctor login.
- Security headers, trusted hosts, CORS controls, CSRF token verification for protected paths.
- Rate limiting on auth and SOS endpoints.
- Append-only hash-chained audit events plus integrity verification endpoint.
- CI dependency and container security scanning.

## Residual Risks and Follow-ups
- Replace in-memory session/grant stores with durable persistence.
- Enforce TLS certificate pinning for high-trust clinical clients.
- Integrate managed KMS-backed secrets provider in deployed environments.
- Add anomaly detection for unusual access patterns and velocity.
