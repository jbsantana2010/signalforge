-- Sprint 4D: Revenue intelligence columns on orgs
ALTER TABLE orgs ADD COLUMN IF NOT EXISTS avg_deal_value NUMERIC DEFAULT 0;
ALTER TABLE orgs ADD COLUMN IF NOT EXISTS close_rate_percent NUMERIC DEFAULT 0;
