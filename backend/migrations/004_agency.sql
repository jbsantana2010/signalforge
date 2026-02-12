-- Agencies (white-label / agency layer)
CREATE TABLE IF NOT EXISTS agencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Link orgs to agencies
ALTER TABLE orgs ADD COLUMN IF NOT EXISTS agency_id UUID REFERENCES agencies(id);
CREATE INDEX IF NOT EXISTS idx_orgs_agency_id ON orgs(agency_id);
