-- 018_call_retry_jobs.sql
-- Minimal persistence for call retries only.
--
-- SCOPE: This table is intentionally not a generic job queue.
-- It handles one thing: surviving server restarts between the moment a call
-- fails and the moment we retry it (~2 min later). Prior implementation used
-- asyncio.sleep(120) in-process, which was lost on restart and broke the
-- 60-second-response SLA we sell.
--
-- If we need another retry type (email, bridge-redial, etc.), add a new
-- narrowly-scoped table OR revisit with a full queue design. Do NOT
-- generalize this one.
--
-- Claim pattern: SELECT ... FOR UPDATE SKIP LOCKED inside a CTE so multiple
-- workers (future) are safe. Single-worker today.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS call_retry_jobs (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id         UUID        NOT NULL REFERENCES leads(id)   ON DELETE CASCADE,
    funnel_id       UUID        NOT NULL REFERENCES funnels(id) ON DELETE CASCADE,
    attempt_number  INT         NOT NULL,
    run_at          TIMESTAMPTZ NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'done', 'failed', 'cancelled')),
    locked_by       TEXT        NULL,
    locked_at       TIMESTAMPTZ NULL,
    last_error      TEXT        NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Claim index: pending rows whose run_at is due, ordered by run_at.
CREATE INDEX IF NOT EXISTS idx_call_retry_jobs_due
    ON call_retry_jobs (run_at)
    WHERE status = 'pending';

-- Lookup by lead (debugging, deduplication).
CREATE INDEX IF NOT EXISTS idx_call_retry_jobs_lead
    ON call_retry_jobs (lead_id);

-- Startup-recovery index: rows a dead worker left 'in_progress'.
CREATE INDEX IF NOT EXISTS idx_call_retry_jobs_stuck
    ON call_retry_jobs (locked_at)
    WHERE status = 'in_progress';
