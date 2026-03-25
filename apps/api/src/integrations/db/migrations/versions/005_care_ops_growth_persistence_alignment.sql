BEGIN;

-- M08/M07/M09/M10/M11 persistence alignment with current in-memory service contracts.

CREATE SCHEMA IF NOT EXISTS medication;
CREATE SCHEMA IF NOT EXISTS notifications;
CREATE SCHEMA IF NOT EXISTS sos;
CREATE SCHEMA IF NOT EXISTS marketplace;
CREATE SCHEMA IF NOT EXISTS billing;

-- Medication reminder engine (aligned to modules/medication_reminders/service.py)
CREATE TABLE IF NOT EXISTS medication.reminder_schedules (
  id TEXT PRIMARY KEY,
  subject_user_id TEXT NOT NULL,
  medication_name TEXT NOT NULL,
  dosage TEXT NOT NULL,
  reminder_message TEXT NOT NULL,
  interval_minutes INTEGER NOT NULL CHECK (interval_minutes >= 1),
  next_due_at TIMESTAMPTZ NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_medication_reminder_schedules_subject_active
  ON medication.reminder_schedules(subject_user_id, active);

CREATE TABLE IF NOT EXISTS medication.reminders_v2 (
  id TEXT PRIMARY KEY,
  schedule_id TEXT NOT NULL REFERENCES medication.reminder_schedules(id) ON DELETE CASCADE,
  subject_user_id TEXT NOT NULL,
  due_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'dispatched')),
  dispatch_key TEXT NOT NULL UNIQUE,
  dispatched_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_medication_reminders_v2_due_status
  ON medication.reminders_v2(due_at, status);

CREATE TABLE IF NOT EXISTS medication.adherence_records (
  id TEXT PRIMARY KEY,
  reminder_id TEXT NOT NULL REFERENCES medication.reminders_v2(id) ON DELETE CASCADE,
  schedule_id TEXT NOT NULL REFERENCES medication.reminder_schedules(id) ON DELETE CASCADE,
  subject_user_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('taken', 'skipped', 'missed')),
  recorded_by_user_id TEXT NOT NULL,
  notes TEXT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_medication_adherence_records_subject_time
  ON medication.adherence_records(subject_user_id, recorded_at DESC);

-- Notification engine (aligned to modules/notifications/service.py)
CREATE TABLE IF NOT EXISTS notifications.user_preferences (
  user_id TEXT PRIMARY KEY,
  enabled_channels TEXT[] NOT NULL DEFAULT ARRAY['email', 'sms', 'push', 'in_app']::TEXT[],
  quiet_hours_start_utc SMALLINT CHECK (quiet_hours_start_utc BETWEEN 0 AND 23),
  quiet_hours_end_utc SMALLINT CHECK (quiet_hours_end_utc BETWEEN 0 AND 23),
  locale TEXT NOT NULL DEFAULT 'en-US',
  accessibility_plain_text BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications.deliveries_v2 (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  recipient_user_id TEXT NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('email', 'sms', 'push', 'in_app')),
  message TEXT NOT NULL,
  priority TEXT NOT NULL CHECK (priority IN ('routine', 'urgent', 'critical')),
  status TEXT NOT NULL CHECK (status IN ('queued', 'sent', 'delivered', 'failed', 'suppressed')),
  dedup_key TEXT,
  provider_name TEXT NOT NULL,
  provider_message_id TEXT,
  fallback_from_channel TEXT CHECK (fallback_from_channel IN ('email', 'sms', 'push', 'in_app')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sent_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  failed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_notifications_deliveries_v2_recipient_created
  ON notifications.deliveries_v2(recipient_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_deliveries_v2_status
  ON notifications.deliveries_v2(status);
CREATE INDEX IF NOT EXISTS idx_notifications_deliveries_v2_dedup
  ON notifications.deliveries_v2(dedup_key)
  WHERE dedup_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS notifications.provider_callbacks_v2 (
  id BIGSERIAL PRIMARY KEY,
  delivery_id TEXT NOT NULL REFERENCES notifications.deliveries_v2(id) ON DELETE CASCADE,
  provider_name TEXT NOT NULL,
  external_status TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notifications_provider_callbacks_delivery
  ON notifications.provider_callbacks_v2(delivery_id);

-- SOS domain (aligned to modules/sos_alerting/service.py)
CREATE TABLE IF NOT EXISTS sos.incidents_v2 (
  id TEXT PRIMARY KEY,
  subject_user_id TEXT NOT NULL,
  initiated_by_user_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('created', 'escalated', 'acknowledged', 'resolved')),
  severity TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  acknowledged_by TEXT,
  acknowledged_at TIMESTAMPTZ,
  resolved_by TEXT,
  resolved_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);
CREATE INDEX IF NOT EXISTS idx_sos_incidents_v2_subject_status
  ON sos.incidents_v2(subject_user_id, status);

CREATE TABLE IF NOT EXISTS sos.escalation_hops_v2 (
  id BIGSERIAL PRIMARY KEY,
  incident_id TEXT NOT NULL REFERENCES sos.incidents_v2(id) ON DELETE CASCADE,
  level INTEGER NOT NULL CHECK (level >= 1),
  recipients TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  target_roles TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  delay_seconds INTEGER NOT NULL CHECK (delay_seconds >= 0),
  retry_delay_seconds INTEGER NOT NULL DEFAULT 60 CHECK (retry_delay_seconds >= 0),
  max_retries INTEGER NOT NULL DEFAULT 2 CHECK (max_retries >= 0),
  retries_attempted INTEGER NOT NULL DEFAULT 0 CHECK (retries_attempted >= 0),
  fallback_recipients TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  fallback_roles TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
  timed_out BOOLEAN NOT NULL DEFAULT FALSE,
  next_attempt_at TIMESTAMPTZ NOT NULL,
  notified_at TIMESTAMPTZ NOT NULL,
  UNIQUE (incident_id, level)
);
CREATE INDEX IF NOT EXISTS idx_sos_escalation_hops_v2_incident
  ON sos.escalation_hops_v2(incident_id);

CREATE TABLE IF NOT EXISTS sos.timeline_events_v2 (
  id TEXT PRIMARY KEY,
  incident_id TEXT NOT NULL REFERENCES sos.incidents_v2(id) ON DELETE CASCADE,
  occurred_at TIMESTAMPTZ NOT NULL,
  event_type TEXT NOT NULL,
  detail TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);
CREATE INDEX IF NOT EXISTS idx_sos_timeline_events_v2_incident_time
  ON sos.timeline_events_v2(incident_id, occurred_at);

-- Marketplace domain (aligned to modules/caregiver_marketplace/service.py)
CREATE TABLE IF NOT EXISTS marketplace.caregivers_v2 (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  bio TEXT,
  skills TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  location TEXT NOT NULL,
  languages TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  geography TEXT,
  availability TEXT NOT NULL,
  rating NUMERIC(4, 2) NOT NULL DEFAULT 0,
  ratings_count INTEGER NOT NULL DEFAULT 0,
  trust_score NUMERIC(5, 3) NOT NULL DEFAULT 0,
  verification_status TEXT NOT NULL CHECK (verification_status IN ('draft', 'submitted', 'pending', 'approved', 'rejected')),
  moderation_status TEXT NOT NULL DEFAULT 'active',
  recommendation_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  dynamic_pricing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketplace_caregivers_v2_search
  ON marketplace.caregivers_v2(location, verification_status, moderation_status);

CREATE TABLE IF NOT EXISTS marketplace.credentials_v2 (
  id TEXT PRIMARY KEY,
  caregiver_id TEXT NOT NULL REFERENCES marketplace.caregivers_v2(id) ON DELETE CASCADE,
  credential_type TEXT NOT NULL,
  document_ref TEXT,
  issuer TEXT,
  status TEXT NOT NULL CHECK (status IN ('draft', 'submitted', 'pending', 'approved', 'rejected')),
  review_notes TEXT,
  reviewed_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketplace_credentials_v2_caregiver
  ON marketplace.credentials_v2(caregiver_id, status);

CREATE TABLE IF NOT EXISTS marketplace.bookings_v2 (
  id TEXT PRIMARY KEY,
  caregiver_id TEXT NOT NULL REFERENCES marketplace.caregivers_v2(id) ON DELETE RESTRICT,
  family_user_id TEXT NOT NULL,
  start_time TEXT NOT NULL,
  notes TEXT,
  status TEXT NOT NULL CHECK (status IN ('requested', 'accepted', 'rejected', 'cancelled', 'confirmed', 'completed')),
  reviewed_by_caregiver BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketplace_bookings_v2_family_status
  ON marketplace.bookings_v2(family_user_id, status);

CREATE TABLE IF NOT EXISTS marketplace.ratings_v2 (
  id TEXT PRIMARY KEY,
  caregiver_id TEXT NOT NULL REFERENCES marketplace.caregivers_v2(id) ON DELETE CASCADE,
  family_user_id TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
  comment TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketplace_ratings_v2_caregiver
  ON marketplace.ratings_v2(caregiver_id, created_at DESC);

CREATE TABLE IF NOT EXISTS marketplace.incident_reports_v2 (
  id TEXT PRIMARY KEY,
  caregiver_id TEXT NOT NULL REFERENCES marketplace.caregivers_v2(id) ON DELETE CASCADE,
  reported_by_user_id TEXT NOT NULL,
  severity TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  moderation_action TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketplace_incident_reports_v2_status
  ON marketplace.incident_reports_v2(status, created_at DESC);

CREATE TABLE IF NOT EXISTS marketplace.extension_hooks (
  id SMALLINT PRIMARY KEY CHECK (id = 1),
  pricing_strategy TEXT NOT NULL DEFAULT 'flat',
  recommendation_strategy TEXT NOT NULL DEFAULT 'rule_v1',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO marketplace.extension_hooks (id, pricing_strategy, recommendation_strategy)
VALUES (1, 'flat', 'rule_v1')
ON CONFLICT (id) DO NOTHING;

-- Subscription domain (aligned to modules/subscriptions/service.py)
CREATE TABLE IF NOT EXISTS billing.plan_catalog_v2 (
  code TEXT PRIMARY KEY CHECK (code IN ('free', 'plus', 'clinical')),
  name TEXT NOT NULL,
  price_monthly_cents INTEGER NOT NULL CHECK (price_monthly_cents >= 0),
  trial_days INTEGER NOT NULL DEFAULT 14 CHECK (trial_days >= 0),
  grace_days INTEGER NOT NULL DEFAULT 7 CHECK (grace_days >= 0),
  features JSONB NOT NULL DEFAULT '{}'::JSONB,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO billing.plan_catalog_v2 (code, name, price_monthly_cents, trial_days, grace_days, features)
VALUES
  ('free', 'Free', 0, 0, 0, '{"marketplace.booking":false,"advanced.analytics":false,"billing.portal":false,"sos.premium_cascade":false}'::JSONB),
  ('plus', 'Plus', 7900, 14, 7, '{"marketplace.booking":true,"advanced.analytics":true,"billing.portal":true,"sos.premium_cascade":true}'::JSONB),
  ('clinical', 'Clinical', 12900, 21, 10, '{"marketplace.booking":true,"advanced.analytics":true,"billing.portal":true,"sos.premium_cascade":true,"doctor.collaboration":true}'::JSONB)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS billing.subscription_states_v2 (
  user_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  plan_code TEXT NOT NULL REFERENCES billing.plan_catalog_v2(code),
  status TEXT NOT NULL CHECK (status IN ('trialing', 'active', 'grace_period', 'past_due', 'cancelled', 'churned')),
  payment_provider TEXT NOT NULL DEFAULT 'demo',
  period_start_at TIMESTAMPTZ,
  period_end_at TIMESTAMPTZ,
  trial_ends_at TIMESTAMPTZ,
  grace_ends_at TIMESTAMPTZ,
  dunning_attempts INTEGER NOT NULL DEFAULT 0 CHECK (dunning_attempts >= 0),
  auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
  cancelled_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_billing_subscription_states_v2_plan_status
  ON billing.subscription_states_v2(plan_code, status);

CREATE TABLE IF NOT EXISTS billing.invoices_v2 (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  plan_code TEXT NOT NULL REFERENCES billing.plan_catalog_v2(code),
  amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
  currency TEXT NOT NULL DEFAULT 'USD',
  status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'failed', 'void')),
  provider TEXT NOT NULL DEFAULT 'demo',
  issued_at TIMESTAMPTZ NOT NULL,
  paid_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);
CREATE INDEX IF NOT EXISTS idx_billing_invoices_v2_user_issued
  ON billing.invoices_v2(user_id, issued_at DESC);

CREATE TABLE IF NOT EXISTS billing.payment_events_v2 (
  event_id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  event_type TEXT NOT NULL,
  user_id TEXT NOT NULL,
  invoice_id TEXT,
  amount_cents INTEGER,
  currency TEXT NOT NULL DEFAULT 'USD',
  status TEXT NOT NULL DEFAULT 'received',
  received_at TIMESTAMPTZ NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);
CREATE INDEX IF NOT EXISTS idx_billing_payment_events_v2_user_time
  ON billing.payment_events_v2(user_id, received_at DESC);

CREATE TABLE IF NOT EXISTS billing.conversion_events_v2 (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  from_plan TEXT NOT NULL,
  to_plan TEXT NOT NULL,
  event_type TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);
CREATE INDEX IF NOT EXISTS idx_billing_conversion_events_v2_user_time
  ON billing.conversion_events_v2(user_id, occurred_at DESC);

COMMIT;
