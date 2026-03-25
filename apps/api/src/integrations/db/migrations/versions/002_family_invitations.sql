CREATE TABLE IF NOT EXISTS family.invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  family_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  parent_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL,
  invitation_token TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
  expires_at TIMESTAMPTZ NOT NULL,
  decided_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (family_user_id, parent_user_id, status)
);

CREATE INDEX IF NOT EXISTS idx_family_invitations_parent_user ON family.invitations(parent_user_id);
CREATE INDEX IF NOT EXISTS idx_family_invitations_family_user ON family.invitations(family_user_id);
CREATE INDEX IF NOT EXISTS idx_family_invitations_status ON family.invitations(status);
