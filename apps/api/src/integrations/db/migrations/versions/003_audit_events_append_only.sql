CREATE TABLE IF NOT EXISTS audit.audit_events (
  id BIGSERIAL PRIMARY KEY,
  event_uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  user_id UUID REFERENCES identity.users(id),
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_audit_events_user_id ON audit.audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_audit_events_action ON audit.audit_events(action);
CREATE INDEX IF NOT EXISTS idx_audit_audit_events_occurred_at ON audit.audit_events(occurred_at);

CREATE OR REPLACE FUNCTION audit.prevent_mutation_on_audit_events()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit events are append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_mutation_audit_events ON audit.audit_events;
CREATE TRIGGER trg_prevent_mutation_audit_events
BEFORE UPDATE OR DELETE ON audit.audit_events
FOR EACH ROW
EXECUTE FUNCTION audit.prevent_mutation_on_audit_events();
