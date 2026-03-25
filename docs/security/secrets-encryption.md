# Secrets and Encryption Controls

## Secrets Management Strategy
- Local development: environment variables from .env with non-production values.
- Staging/production: load secrets from managed secret manager and inject at runtime.
- Key references: use external secret reference IDs, not raw values, in IaC and CI.

## JWT and Session Security
- Access/refresh tokens are signed with KID headers.
- Active and previous signing keys can coexist for seamless rotation.
- Refresh tokens are rotated and old JTIs are revocation-tracked.

## Data-in-Transit Controls
- TLS required for web and API ingress.
- Internal service traffic should use TLS in staging and production overlays.
- Object storage endpoint must use HTTPS in non-local environments.

## Data-at-Rest Controls
- PostgreSQL disk encryption enabled via cloud-managed storage encryption.
- Object storage server-side encryption enabled and bucket access minimized.
- Backups encrypted at storage target and retention-controlled.

## Rotation Cadence
- JWT signing keys: every 30 days or immediately after suspected compromise.
- Provider credentials (SMS/email/payment): every 90 days.
- Database and storage credentials: every 60 days.
