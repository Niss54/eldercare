BEGIN;

INSERT INTO identity.roles (role_key, role_name)
VALUES
  ('admin', 'Administrator'),
  ('family_member', 'Family Member'),
  ('parent', 'Parent'),
  ('caregiver', 'Caregiver'),
  ('doctor', 'Doctor')
ON CONFLICT (role_key) DO NOTHING;

INSERT INTO identity.permissions (permission_key, permission_name)
VALUES
  ('health.read', 'Read health records'),
  ('health.write', 'Write health records'),
  ('consent.manage', 'Manage consent grants'),
  ('sos.trigger', 'Trigger SOS incident'),
  ('marketplace.book', 'Book marketplace caregiver'),
  ('billing.manage', 'Manage billing and plans'),
  ('admin.analytics.read', 'Read analytics dashboards')
ON CONFLICT (permission_key) DO NOTHING;

INSERT INTO billing.plans (plan_key, plan_name, monthly_price_cents, currency, features)
VALUES
  ('essential', 'Essential', 3900, 'USD', '{"max_family_members":2,"sos_priority":"standard"}'::jsonb),
  ('plus', 'Plus', 7900, 'USD', '{"max_family_members":10,"sos_priority":"priority"}'::jsonb),
  ('clinical', 'Clinical', 12900, 'USD', '{"doctor_collaboration":true,"advanced_analytics":true}'::jsonb)
ON CONFLICT (plan_key) DO NOTHING;

INSERT INTO notifications.templates (template_key, channel, locale, priority, subject_template, body_template)
VALUES
  ('medication_due_sms', 'sms', 'en-US', 'urgent', 'Medication reminder', 'It is time to take your scheduled medication.'),
  ('sos_created_push', 'push', 'en-US', 'critical', 'SOS triggered', 'Emergency SOS has been triggered and responders are being notified.'),
  ('weekly_digest_email', 'email', 'en-US', 'routine', 'Weekly care summary', 'Your weekly care summary is ready in the family portal.')
ON CONFLICT (template_key) DO NOTHING;

COMMIT;
