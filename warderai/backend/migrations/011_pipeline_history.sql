-- 011_pipeline_history.sql: Sprint 6 – Pipeline foundation
-- Adds next-action scheduling, stage history table, and updated indexes.
-- Renames stage 'appointment' → 'proposal' to match sales lifecycle spec.

-- 1. Add new pipeline fields to leads
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS next_action_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS next_action_note TEXT;

-- 2. Rename existing 'appointment' stage to 'proposal'
UPDATE leads SET stage = 'proposal' WHERE stage = 'appointment';

-- 3. Create lead_stage_history table
CREATE TABLE IF NOT EXISTS lead_stage_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    from_stage TEXT,
    to_stage TEXT NOT NULL,
    changed_by_user_id UUID,
    reason TEXT,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Indexes for stage history
CREATE INDEX IF NOT EXISTS idx_lead_stage_history_lead
    ON lead_stage_history (lead_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_lead_stage_history_org
    ON lead_stage_history (org_id, created_at DESC);

-- 5. Composite indexes on leads for pipeline queries
CREATE INDEX IF NOT EXISTS idx_leads_org_stage
    ON leads (org_id, stage);

CREATE INDEX IF NOT EXISTS idx_leads_org_next_action
    ON leads (org_id, next_action_at);
