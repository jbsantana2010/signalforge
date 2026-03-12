-- Migration 014: Inbound Messages (Reply Intelligence V1)
-- Idempotent: uses IF NOT EXISTS / DO NOTHING patterns

CREATE TABLE IF NOT EXISTS inbound_messages (
    id                UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id           UUID        NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    org_id            UUID        NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    channel           TEXT        NOT NULL,   -- sms | email
    message_body      TEXT        NOT NULL,
    classification    TEXT        NULL,        -- interested | price | timing | info | not_interested | human_needed | unknown
    suggested_response TEXT       NULL,
    metadata_json     JSONB       NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_inbound_messages_lead_id    ON inbound_messages(lead_id);
CREATE INDEX IF NOT EXISTS idx_inbound_messages_org_id     ON inbound_messages(org_id);
CREATE INDEX IF NOT EXISTS idx_inbound_messages_created_at ON inbound_messages(created_at);
