-- Migration 017: Rep contact profiles
-- Stores rep phone/name for correct notification routing.
-- Idempotent.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS rep_contacts (
    id         UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id     UUID        NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    email      TEXT        NOT NULL,
    phone      TEXT        NULL,
    full_name  TEXT        NULL,
    is_active  BOOLEAN     NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_rep_contacts_org_email UNIQUE (org_id, email)
);

CREATE INDEX IF NOT EXISTS idx_rep_contacts_org_id ON rep_contacts (org_id);
CREATE INDEX IF NOT EXISTS idx_rep_contacts_email  ON rep_contacts (email);
