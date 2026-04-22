-- 010_pipeline.sql: Add pipeline stage tracking to leads
-- Adds stage, deal_amount, and stage_updated_at columns for real revenue tracking.

ALTER TABLE leads
ADD COLUMN IF NOT EXISTS stage TEXT DEFAULT 'new',
ADD COLUMN IF NOT EXISTS deal_amount NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS stage_updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
