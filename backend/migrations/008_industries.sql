-- 008_industries.sql: Industry templates for vertical-specific onboarding

-- Industries table
CREATE TABLE IF NOT EXISTS industries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Industry templates table
CREATE TABLE IF NOT EXISTS industry_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    industry_id UUID NOT NULL REFERENCES industries(id) ON DELETE CASCADE,
    default_funnel_json JSONB NOT NULL,
    default_sequence_json JSONB NOT NULL,
    default_scoring_json JSONB NOT NULL,
    default_avg_deal_value NUMERIC NOT NULL DEFAULT 5000,
    default_close_rate_percent NUMERIC NOT NULL DEFAULT 10,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraint so each industry has at most one template
CREATE UNIQUE INDEX IF NOT EXISTS idx_industry_templates_industry_id
    ON industry_templates(industry_id);

-- Add industry_id to orgs
ALTER TABLE orgs ADD COLUMN IF NOT EXISTS industry_id UUID REFERENCES industries(id);
CREATE INDEX IF NOT EXISTS idx_orgs_industry_id ON orgs(industry_id);

-- Add scoring_config to orgs (org-level scoring rubric from industry template)
ALTER TABLE orgs ADD COLUMN IF NOT EXISTS scoring_config JSONB;

-- Back-compat: insert generic industry if missing
INSERT INTO industries (slug, name, description)
VALUES ('generic', 'Generic', 'Default industry profile for general-purpose lead capture')
ON CONFLICT (slug) DO NOTHING;

-- Back-compat: insert generic template if missing
INSERT INTO industry_templates (industry_id, default_funnel_json, default_sequence_json, default_scoring_json, default_avg_deal_value, default_close_rate_percent)
SELECT
    i.id,
    '{"languages":["en"],"steps":[{"id":"service","title":{"en":"What service do you need?"},"fields":[{"key":"service","type":"select","required":true,"label":{"en":"Service"},"options":[{"value":"solar","label":{"en":"Solar Installation"}},{"value":"roofing","label":{"en":"Roofing"}},{"value":"other","label":{"en":"Other"}}]}]},{"id":"contact_info","title":{"en":"Your Information"},"fields":[{"key":"zip_code","type":"text","required":true,"label":{"en":"Zip Code"}},{"key":"name","type":"text","required":true,"label":{"en":"Full Name"}}]},{"id":"phone_info","title":{"en":"Contact Preferences"},"fields":[{"key":"phone","type":"tel","required":true,"label":{"en":"Phone Number"}},{"key":"contact_time","type":"select","required":false,"label":{"en":"Best time to call"},"options":[{"value":"morning","label":{"en":"Morning"}},{"value":"afternoon","label":{"en":"Afternoon"}},{"value":"evening","label":{"en":"Evening"}}]}]}]}'::jsonb,
    '{"steps":[{"delay_minutes":0,"message":"Thanks for your request, {{name}}! We''ll be in touch shortly."},{"delay_minutes":1440,"message":"Hi {{name}}, just checking in on your inquiry. Any questions?"},{"delay_minutes":4320,"message":"Hi {{name}}, we''d love to help — reply to schedule a call!"}]}'::jsonb,
    '{"rubric":"Score leads 0-100 based on intent signals, budget indicators, and timeline urgency."}'::jsonb,
    5000,
    10
FROM industries i
WHERE i.slug = 'generic'
ON CONFLICT (industry_id) DO NOTHING;

-- Set orgs.industry_id to generic for any NULL orgs
UPDATE orgs
SET industry_id = (SELECT id FROM industries WHERE slug = 'generic')
WHERE industry_id IS NULL;
