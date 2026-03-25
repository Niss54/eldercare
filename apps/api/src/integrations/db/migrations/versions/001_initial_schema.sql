BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS family;
CREATE SCHEMA IF NOT EXISTS consent;
CREATE SCHEMA IF NOT EXISTS health;
CREATE SCHEMA IF NOT EXISTS medication;
CREATE SCHEMA IF NOT EXISTS sos;
CREATE SCHEMA IF NOT EXISTS notifications;
CREATE SCHEMA IF NOT EXISTS marketplace;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS identity.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'locked', 'disabled')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS identity.profiles (
  user_id UUID PRIMARY KEY REFERENCES identity.users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL,
  phone_e164 TEXT,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  locale TEXT NOT NULL DEFAULT 'en-US',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS identity.roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_key TEXT NOT NULL UNIQUE,
  role_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS identity.permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  permission_key TEXT NOT NULL UNIQUE,
  permission_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS identity.role_permissions (
  role_id UUID NOT NULL REFERENCES identity.roles(id) ON DELETE CASCADE,
  permission_id UUID NOT NULL REFERENCES identity.permissions(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS identity.user_roles (
  user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES identity.roles(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS identity.sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  refresh_token_hash TEXT NOT NULL UNIQUE,
  user_agent TEXT,
  ip_address INET,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_identity_sessions_user_id ON identity.sessions(user_id);

CREATE TABLE IF NOT EXISTS family.relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  family_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  parent_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('invited', 'approved', 'rejected', 'revoked')),
  invited_by_user_id UUID NOT NULL REFERENCES identity.users(id),
  invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  approved_by_user_id UUID REFERENCES identity.users(id),
  approved_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (family_user_id, parent_user_id)
);
CREATE INDEX IF NOT EXISTS idx_family_relationships_parent_user ON family.relationships(parent_user_id);

CREATE TABLE IF NOT EXISTS consent.consent_grants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  grantee_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  domain_key TEXT NOT NULL,
  action_key TEXT NOT NULL,
  scope JSONB NOT NULL DEFAULT '{}'::JSONB,
  status TEXT NOT NULL CHECK (status IN ('requested', 'granted', 'revoked', 'expired')),
  granted_by_user_id UUID REFERENCES identity.users(id),
  reason TEXT,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  granted_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_consent_grants_subject_grantee ON consent.consent_grants(subject_user_id, grantee_user_id);
CREATE INDEX IF NOT EXISTS idx_consent_grants_status ON consent.consent_grants(status);

CREATE TABLE IF NOT EXISTS health.records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  created_by_user_id UUID NOT NULL REFERENCES identity.users(id),
  record_type TEXT NOT NULL,
  title TEXT NOT NULL,
  notes TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  occurred_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_health_records_parent_user ON health.records(parent_user_id);
CREATE INDEX IF NOT EXISTS idx_health_records_record_type ON health.records(record_type);

CREATE TABLE IF NOT EXISTS health.record_objects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  record_id UUID NOT NULL REFERENCES health.records(id) ON DELETE CASCADE,
  bucket_name TEXT NOT NULL,
  object_key TEXT NOT NULL,
  object_version TEXT,
  content_type TEXT,
  object_size BIGINT NOT NULL DEFAULT 0,
  checksum_sha256 TEXT,
  encrypted BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (bucket_name, object_key, COALESCE(object_version, ''))
);
CREATE INDEX IF NOT EXISTS idx_health_record_objects_record_id ON health.record_objects(record_id);

CREATE TABLE IF NOT EXISTS medication.schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  prescribed_by_user_id UUID REFERENCES identity.users(id),
  medication_name TEXT NOT NULL,
  dosage TEXT NOT NULL,
  route TEXT,
  frequency_rule TEXT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS medication.reminders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  schedule_id UUID NOT NULL REFERENCES medication.schedules(id) ON DELETE CASCADE,
  due_at TIMESTAMPTZ NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending', 'sent', 'acked', 'missed', 'escalated')),
  sent_at TIMESTAMPTZ,
  acknowledged_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_medication_reminders_due_at ON medication.reminders(due_at);

CREATE TABLE IF NOT EXISTS medication.adherence_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reminder_id UUID NOT NULL REFERENCES medication.reminders(id) ON DELETE CASCADE,
  actor_user_id UUID NOT NULL REFERENCES identity.users(id),
  status TEXT NOT NULL CHECK (status IN ('taken', 'skipped', 'late')),
  evidence JSONB NOT NULL DEFAULT '{}'::JSONB,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS medication.escalations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reminder_id UUID NOT NULL REFERENCES medication.reminders(id) ON DELETE CASCADE,
  escalation_level SMALLINT NOT NULL,
  target_role TEXT NOT NULL,
  target_user_id UUID REFERENCES identity.users(id),
  state TEXT NOT NULL CHECK (state IN ('queued', 'dispatched', 'acknowledged', 'failed')),
  dispatched_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sos.incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  opened_by_user_id UUID NOT NULL REFERENCES identity.users(id),
  state TEXT NOT NULL CHECK (state IN ('created', 'acknowledged', 'escalated', 'resolved', 'cancelled')),
  severity TEXT NOT NULL CHECK (severity IN ('routine', 'urgent', 'critical')),
  location_text TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  closed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sos_incidents_parent_state ON sos.incidents(parent_user_id, state);

CREATE TABLE IF NOT EXISTS sos.escalation_hops (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id UUID NOT NULL REFERENCES sos.incidents(id) ON DELETE CASCADE,
  hop_order SMALLINT NOT NULL,
  target_role TEXT NOT NULL,
  target_user_id UUID REFERENCES identity.users(id),
  channel TEXT NOT NULL,
  timer_seconds INTEGER NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('pending', 'contacted', 'acknowledged', 'timed_out', 'skipped')),
  contacted_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (incident_id, hop_order)
);

CREATE TABLE IF NOT EXISTS sos.responder_acknowledgements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id UUID NOT NULL REFERENCES sos.incidents(id) ON DELETE CASCADE,
  responder_user_id UUID NOT NULL REFERENCES identity.users(id),
  ack_status TEXT NOT NULL CHECK (ack_status IN ('accepted', 'declined', 'resolved')),
  response_notes TEXT,
  responded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications.templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_key TEXT NOT NULL UNIQUE,
  channel TEXT NOT NULL,
  locale TEXT NOT NULL DEFAULT 'en-US',
  priority TEXT NOT NULL CHECK (priority IN ('routine', 'urgent', 'critical')),
  subject_template TEXT,
  body_template TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications.delivery_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL DEFAULT gen_random_uuid(),
  recipient_user_id UUID NOT NULL REFERENCES identity.users(id),
  template_id UUID REFERENCES notifications.templates(id),
  channel TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'sent', 'delivered', 'failed', 'suppressed')),
  provider_name TEXT,
  provider_message_id TEXT,
  dedup_key TEXT,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sent_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  failed_at TIMESTAMPTZ,
  UNIQUE (channel, COALESCE(dedup_key, id::TEXT))
);
CREATE INDEX IF NOT EXISTS idx_notifications_delivery_recipient ON notifications.delivery_attempts(recipient_user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_delivery_status ON notifications.delivery_attempts(status);

CREATE TABLE IF NOT EXISTS notifications.provider_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  delivery_attempt_id UUID NOT NULL REFERENCES notifications.delivery_attempts(id) ON DELETE CASCADE,
  provider_name TEXT NOT NULL,
  response_code TEXT,
  response_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS marketplace.caregiver_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  caregiver_user_id UUID NOT NULL UNIQUE REFERENCES identity.users(id) ON DELETE CASCADE,
  headline TEXT,
  bio TEXT,
  years_experience SMALLINT,
  languages TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  skills TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  hourly_rate_cents INTEGER,
  verified BOOLEAN NOT NULL DEFAULT FALSE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS marketplace.caregiver_credentials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  caregiver_profile_id UUID NOT NULL REFERENCES marketplace.caregiver_profiles(id) ON DELETE CASCADE,
  credential_type TEXT NOT NULL,
  issuer TEXT,
  credential_number TEXT,
  status TEXT NOT NULL CHECK (status IN ('submitted', 'verified', 'rejected', 'expired')),
  expires_on DATE,
  document_ref TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  reviewed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS marketplace.caregiver_availability (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  caregiver_profile_id UUID NOT NULL REFERENCES marketplace.caregiver_profiles(id) ON DELETE CASCADE,
  day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS marketplace.matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  requester_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  parent_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  caregiver_profile_id UUID NOT NULL REFERENCES marketplace.caregiver_profiles(id),
  score NUMERIC(5, 2) NOT NULL,
  strategy TEXT NOT NULL DEFAULT 'rule_v1',
  rationale JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_marketplace_matches_requester_parent ON marketplace.matches(requester_user_id, parent_user_id);

CREATE TABLE IF NOT EXISTS marketplace.bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id UUID REFERENCES marketplace.matches(id),
  family_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  caregiver_profile_id UUID NOT NULL REFERENCES marketplace.caregiver_profiles(id),
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('requested', 'accepted', 'rejected', 'cancelled', 'completed')),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing.plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_key TEXT NOT NULL UNIQUE,
  plan_name TEXT NOT NULL,
  monthly_price_cents INTEGER NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  features JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing.customer_entitlements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  plan_id UUID NOT NULL REFERENCES billing.plans(id),
  status TEXT NOT NULL CHECK (status IN ('trial', 'active', 'grace', 'past_due', 'cancelled')),
  effective_from TIMESTAMPTZ NOT NULL,
  effective_to TIMESTAMPTZ,
  feature_overrides JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_billing_entitlements_customer ON billing.customer_entitlements(customer_user_id);

CREATE TABLE IF NOT EXISTS billing.invoice_pointers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entitlement_id UUID NOT NULL REFERENCES billing.customer_entitlements(id) ON DELETE CASCADE,
  provider_name TEXT NOT NULL,
  provider_invoice_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'USD',
  status TEXT NOT NULL CHECK (status IN ('open', 'paid', 'void', 'failed')),
  invoice_document_ref TEXT,
  issued_at TIMESTAMPTZ NOT NULL,
  paid_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (provider_name, provider_invoice_id)
);

CREATE TABLE IF NOT EXISTS audit.events (
  id BIGSERIAL PRIMARY KEY,
  event_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor_user_id UUID REFERENCES identity.users(id),
  subject_user_id UUID REFERENCES identity.users(id),
  module_key TEXT NOT NULL,
  action_key TEXT NOT NULL,
  resource_type TEXT,
  resource_id TEXT,
  request_id TEXT,
  ip_address INET,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  prev_hash TEXT,
  event_hash TEXT NOT NULL,
  chain_index BIGINT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_audit_events_occurred_at ON audit.events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_audit_events_module_action ON audit.events(module_key, action_key);

CREATE TABLE IF NOT EXISTS analytics.user_activity_daily (
  activity_date DATE NOT NULL,
  role_key TEXT NOT NULL,
  active_users INTEGER NOT NULL DEFAULT 0,
  sessions_started INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (activity_date, role_key)
);

CREATE TABLE IF NOT EXISTS analytics.incident_rollups_hourly (
  hour_bucket TIMESTAMPTZ NOT NULL,
  severity TEXT NOT NULL,
  created_count INTEGER NOT NULL DEFAULT 0,
  acknowledged_count INTEGER NOT NULL DEFAULT 0,
  resolved_count INTEGER NOT NULL DEFAULT 0,
  median_ack_seconds INTEGER,
  PRIMARY KEY (hour_bucket, severity)
);

CREATE TABLE IF NOT EXISTS analytics.notification_rollups_hourly (
  hour_bucket TIMESTAMPTZ NOT NULL,
  channel TEXT NOT NULL,
  sent_count INTEGER NOT NULL DEFAULT 0,
  delivered_count INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (hour_bucket, channel)
);

CREATE TABLE IF NOT EXISTS analytics.revenue_rollups_monthly (
  month_bucket DATE NOT NULL,
  plan_key TEXT NOT NULL,
  active_subscriptions INTEGER NOT NULL DEFAULT 0,
  mrr_cents BIGINT NOT NULL DEFAULT 0,
  churn_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (month_bucket, plan_key)
);

COMMIT;
