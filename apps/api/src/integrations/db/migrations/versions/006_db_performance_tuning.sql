BEGIN;

-- DB performance tuning: additional indexes for common access paths and sort patterns.

-- Family and consent lookups
CREATE INDEX IF NOT EXISTS idx_family_relationships_family_state
  ON family.relationships(family_user_id, state);
CREATE INDEX IF NOT EXISTS idx_family_relationships_parent_state
  ON family.relationships(parent_user_id, state);

CREATE INDEX IF NOT EXISTS idx_consent_grants_subject_status_expiry
  ON consent.consent_grants(subject_user_id, status, expires_at);
CREATE INDEX IF NOT EXISTS idx_consent_grants_grantee_status_expiry
  ON consent.consent_grants(grantee_user_id, status, expires_at);
CREATE INDEX IF NOT EXISTS idx_consent_grants_domain_action_status
  ON consent.consent_grants(domain_key, action_key, status);

-- Health records list/search
CREATE INDEX IF NOT EXISTS idx_health_records_parent_type_created
  ON health.records(parent_user_id, record_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_records_parent_created
  ON health.records(parent_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_health_health_records_patient_type_created
  ON health.health_records(patient_user_id, record_type, created_at DESC)
  WHERE is_deleted = false;

-- Notifications and realtime operations
CREATE INDEX IF NOT EXISTS idx_notifications_deliveries_v2_recipient_status_created
  ON notifications.deliveries_v2(recipient_user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_deliveries_v2_event
  ON notifications.deliveries_v2(event_id);

-- SOS incident and timeline queries
CREATE INDEX IF NOT EXISTS idx_sos_incidents_v2_status_created
  ON sos.incidents_v2(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sos_incidents_v2_initiator_created
  ON sos.incidents_v2(initiated_by_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sos_timeline_events_v2_type_time
  ON sos.timeline_events_v2(event_type, occurred_at DESC);

-- Marketplace and billing
CREATE INDEX IF NOT EXISTS idx_marketplace_bookings_v2_caregiver_status_created
  ON marketplace.bookings_v2(caregiver_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_bookings_v2_created
  ON marketplace.bookings_v2(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_billing_subscription_states_v2_status_updated
  ON billing.subscription_states_v2(status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_billing_subscription_states_v2_tenant_status
  ON billing.subscription_states_v2(tenant_id, status);

-- Audit/compliance retrieval
CREATE INDEX IF NOT EXISTS idx_audit_audit_events_resource_time
  ON audit.audit_events(resource_type, resource_id, occurred_at DESC);

COMMIT;
