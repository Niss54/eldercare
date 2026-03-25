-- M05.1 Health Records Migration
-- Creates health_records table with JSONB data column and document references

CREATE SCHEMA IF NOT EXISTS health;

CREATE TABLE IF NOT EXISTS health.health_records (
  id TEXT PRIMARY KEY,
  patient_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
  created_by_user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE RESTRICT,
  record_type TEXT NOT NULL CHECK (record_type IN ('medical_history', 'lab_results', 'vitals', 'prescription')),
  data JSONB NOT NULL DEFAULT '{}',
  document_s3_key TEXT,
  document_file_hash TEXT,
  document_mime_type TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_deleted BOOLEAN NOT NULL DEFAULT false
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_health_records_patient_user ON health.health_records(patient_user_id) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_health_records_created_by ON health.health_records(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_health_records_record_type ON health.health_records(record_type) WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_health_records_created_at ON health.health_records(created_at DESC) WHERE is_deleted = false;

-- Full-text search index on JSONB data (optional, for advanced search)
CREATE INDEX IF NOT EXISTS idx_health_records_data_gin ON health.health_records USING GIN (data) WHERE is_deleted = false;

-- Enable RLS on health records table
ALTER TABLE health.health_records ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can read health records for themselves or those they have consent for
DROP POLICY IF EXISTS health_records_select_policy ON health.health_records;
CREATE POLICY health_records_select_policy ON health.health_records
FOR SELECT
USING (
  is_deleted = false
  AND (
    patient_user_id = CAST(current_setting('app.current_user_id') AS UUID)
    OR app.has_active_consent(patient_user_id, CAST(current_setting('app.current_user_id') AS UUID), 'health', 'read')
  )
);

-- RLS Policy: Users can create records for themselves or with consent
DROP POLICY IF EXISTS health_records_insert_policy ON health.health_records;
CREATE POLICY health_records_insert_policy ON health.health_records
FOR INSERT
WITH CHECK (
  patient_user_id = CAST(current_setting('app.current_user_id') AS UUID)
  OR app.has_active_consent(patient_user_id, CAST(current_setting('app.current_user_id') AS UUID), 'health', 'write')
);

-- RLS Policy: Users can update only their own records or records they have write consent for
DROP POLICY IF EXISTS health_records_update_policy ON health.health_records;
CREATE POLICY health_records_update_policy ON health.health_records
FOR UPDATE
USING (
  patient_user_id = CAST(current_setting('app.current_user_id') AS UUID)
  OR app.has_active_consent(patient_user_id, CAST(current_setting('app.current_user_id') AS UUID), 'health', 'write')
);

-- RLS Policy: Users can soft-delete only their own records
DROP POLICY IF EXISTS health_records_delete_policy ON health.health_records;
CREATE POLICY health_records_delete_policy ON health.health_records
FOR DELETE
USING (
  patient_user_id = CAST(current_setting('app.current_user_id') AS UUID)
);
