ALTER TABLE health.records ENABLE ROW LEVEL SECURITY;
ALTER TABLE health.record_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent.consent_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing.customer_entitlements ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS health_records_select_policy ON health.records;
CREATE POLICY health_records_select_policy ON health.records
FOR SELECT
USING (
  app.current_user_id() IS NOT NULL
  AND app.can_read_health_record(parent_user_id, app.current_user_id())
);

DROP POLICY IF EXISTS health_records_modify_policy ON health.records;
CREATE POLICY health_records_modify_policy ON health.records
FOR UPDATE
USING (
  app.current_user_id() IS NOT NULL
  AND app.has_active_consent(parent_user_id, app.current_user_id(), 'health', 'write')
);

DROP POLICY IF EXISTS health_record_objects_select_policy ON health.record_objects;
CREATE POLICY health_record_objects_select_policy ON health.record_objects
FOR SELECT
USING (
  EXISTS (
    SELECT 1
    FROM health.records r
    WHERE r.id = record_id
      AND app.can_read_health_record(r.parent_user_id, app.current_user_id())
  )
);

DROP POLICY IF EXISTS consent_grants_subject_grantee_policy ON consent.consent_grants;
CREATE POLICY consent_grants_subject_grantee_policy ON consent.consent_grants
FOR SELECT
USING (
  app.current_user_id() IS NOT NULL
  AND app.current_user_id() IN (subject_user_id, grantee_user_id)
);

DROP POLICY IF EXISTS billing_entitlements_owner_policy ON billing.customer_entitlements;
CREATE POLICY billing_entitlements_owner_policy ON billing.customer_entitlements
FOR SELECT
USING (
  app.current_user_id() IS NOT NULL
  AND customer_user_id = app.current_user_id()
);
