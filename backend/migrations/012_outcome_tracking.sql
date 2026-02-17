-- Sprint 8: Outcome tracking fields for adaptive intelligence
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS outcome_reason TEXT,
    ADD COLUMN IF NOT EXISTS outcome_note TEXT,
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

-- Index for closed_at queries (insights endpoint)
CREATE INDEX IF NOT EXISTS idx_leads_org_closed ON leads (org_id, closed_at)
    WHERE closed_at IS NOT NULL;
