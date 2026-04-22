-- Org branding columns for white-label
ALTER TABLE orgs ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE orgs ADD COLUMN IF NOT EXISTS logo_url TEXT;
ALTER TABLE orgs ADD COLUMN IF NOT EXISTS primary_color TEXT DEFAULT '#2563eb';
ALTER TABLE orgs ADD COLUMN IF NOT EXISTS support_email TEXT;
