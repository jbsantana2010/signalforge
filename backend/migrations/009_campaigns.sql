-- 009_campaigns.sql: Campaign-level revenue attribution

CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    campaign_name TEXT NOT NULL,
    utm_campaign TEXT NOT NULL,
    ad_spend NUMERIC NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (org_id, utm_campaign)
);

CREATE INDEX IF NOT EXISTS idx_campaigns_org_id ON campaigns(org_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_utm_campaign ON campaigns(utm_campaign);
