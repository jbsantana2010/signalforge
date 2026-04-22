-- Migration 015: lead handoff state
-- Idempotent: adds needs_human, handoff_reason, handoff_at to leads.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'leads' AND column_name = 'needs_human'
    ) THEN
        ALTER TABLE leads ADD COLUMN needs_human BOOLEAN NOT NULL DEFAULT false;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'leads' AND column_name = 'handoff_reason'
    ) THEN
        ALTER TABLE leads ADD COLUMN handoff_reason TEXT NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'leads' AND column_name = 'handoff_at'
    ) THEN
        ALTER TABLE leads ADD COLUMN handoff_at TIMESTAMPTZ NULL;
    END IF;
END $$;

-- Partial index for efficient handoff queue queries
CREATE INDEX IF NOT EXISTS leads_needs_human_idx
    ON leads (org_id, handoff_at DESC)
    WHERE needs_human = true;
