CREATE OR REPLACE FUNCTION app.current_user_id()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_user_id', true), '')::UUID
$$;

CREATE OR REPLACE FUNCTION app.has_active_consent(
  p_subject_user_id UUID,
  p_grantee_user_id UUID,
  p_domain_key TEXT,
  p_action_key TEXT
)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM consent.consent_grants c
    WHERE c.subject_user_id = p_subject_user_id
      AND c.grantee_user_id = p_grantee_user_id
      AND c.domain_key = p_domain_key
      AND c.action_key = p_action_key
      AND c.status = 'granted'
      AND (c.expires_at IS NULL OR c.expires_at > NOW())
  )
$$;

CREATE OR REPLACE FUNCTION app.can_read_health_record(
  p_parent_user_id UUID,
  p_actor_user_id UUID
)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT p_parent_user_id = p_actor_user_id
    OR EXISTS (
      SELECT 1
      FROM family.relationships fr
      WHERE fr.parent_user_id = p_parent_user_id
        AND fr.family_user_id = p_actor_user_id
        AND fr.state = 'approved'
    )
    OR app.has_active_consent(
      p_parent_user_id,
      p_actor_user_id,
      'health',
      'read'
    )
$$;
