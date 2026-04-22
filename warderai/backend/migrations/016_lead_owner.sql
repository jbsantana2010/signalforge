-- 016_lead_owner.sql
-- Add owner_email to leads for rep assignment

ALTER TABLE leads ADD COLUMN IF NOT EXISTS owner_email TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_leads_owner_email
    ON leads (owner_email)
    WHERE owner_email IS NOT NULL;
