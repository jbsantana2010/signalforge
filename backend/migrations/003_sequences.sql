-- Lead follow-up sequences
CREATE TABLE IF NOT EXISTS lead_sequences (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id uuid REFERENCES leads(id) ON DELETE CASCADE,
    step int NOT NULL,
    scheduled_at timestamptz NOT NULL,
    sent_at timestamptz,
    status text DEFAULT 'pending',
    message text
);

CREATE INDEX IF NOT EXISTS idx_lead_sequences_lead_id ON lead_sequences(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_sequences_due ON lead_sequences(status, scheduled_at);

-- Funnel sequence settings
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS sequence_enabled boolean DEFAULT false;
ALTER TABLE funnels ADD COLUMN IF NOT EXISTS sequence_config jsonb;
