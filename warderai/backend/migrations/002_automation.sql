-- Migration 002: Automation columns for leads and funnels

-- ALTER leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags text[];
ALTER TABLE leads ADD COLUMN IF NOT EXISTS priority text;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_summary text;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_score int;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_status text;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS sms_status text;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS call_status text;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS call_attempts int DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS contact_status text;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_contacted_at timestamptz;

-- ALTER funnels table
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS routing_rules jsonb;
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS auto_email_enabled boolean DEFAULT false;
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS auto_sms_enabled boolean DEFAULT false;
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS auto_call_enabled boolean DEFAULT false;
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS notification_emails text[];
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS webhook_url text;
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS rep_phone_number text;
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS twilio_from_number text;
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS working_hours_start int DEFAULT 9;
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS working_hours_end int DEFAULT 19;
