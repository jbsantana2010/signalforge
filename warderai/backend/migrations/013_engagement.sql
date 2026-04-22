-- Migration 013: Engagement Engine V1
-- Idempotent: uses IF NOT EXISTS / DO NOTHING patterns

-- 1) engagement_plans
CREATE TABLE IF NOT EXISTS engagement_plans (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id      UUID        NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    org_id       UUID        NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    funnel_id    UUID        NULL REFERENCES funnels(id) ON DELETE SET NULL,
    status       TEXT        NOT NULL DEFAULT 'active',
    current_step INTEGER     NOT NULL DEFAULT 0,
    paused       BOOLEAN     NOT NULL DEFAULT false,
    escalation_reason TEXT   NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_engagement_plans_lead_id   ON engagement_plans(lead_id);
CREATE INDEX IF NOT EXISTS idx_engagement_plans_org_id    ON engagement_plans(org_id);
CREATE INDEX IF NOT EXISTS idx_engagement_plans_status    ON engagement_plans(status);

-- 2) engagement_steps
CREATE TABLE IF NOT EXISTS engagement_steps (
    id                    UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id               UUID        NOT NULL REFERENCES engagement_plans(id) ON DELETE CASCADE,
    step_order            INTEGER     NOT NULL,
    channel               TEXT        NOT NULL,  -- sms | email | call
    action_type           TEXT        NOT NULL DEFAULT 'send',
    scheduled_for         TIMESTAMPTZ NOT NULL,
    executed_at           TIMESTAMPTZ NULL,
    status                TEXT        NOT NULL DEFAULT 'pending',
    template_key          TEXT        NULL,
    generated_content_json JSONB      NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_engagement_steps_plan_id       ON engagement_steps(plan_id);
CREATE INDEX IF NOT EXISTS idx_engagement_steps_scheduled_for ON engagement_steps(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_engagement_steps_status        ON engagement_steps(status);

-- 3) engagement_events
CREATE TABLE IF NOT EXISTS engagement_events (
    id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id       UUID        NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    org_id        UUID        NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    channel       TEXT        NOT NULL,
    event_type    TEXT        NOT NULL,
    direction     TEXT        NOT NULL,  -- outbound | inbound | system
    content       TEXT        NULL,
    metadata_json JSONB       NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_engagement_events_lead_id    ON engagement_events(lead_id);
CREATE INDEX IF NOT EXISTS idx_engagement_events_org_id     ON engagement_events(org_id);
CREATE INDEX IF NOT EXISTS idx_engagement_events_event_type ON engagement_events(event_type);
CREATE INDEX IF NOT EXISTS idx_engagement_events_created_at ON engagement_events(created_at);
