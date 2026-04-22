"""Minimal persistence layer for call retries.

Scope is intentionally narrow: this module handles ONE retry type (failed
Twilio bridge calls) and is not a generic job queue. See
migrations/018_call_retry_jobs.sql for the rationale.

API:
    enqueue(pool, lead_id, funnel_id, attempt_number, delay_seconds)
    claim_due(pool, worker_id, limit)   -> list[dict]
    mark_done(pool, job_id)
    mark_failed(pool, job_id, error)
    recover_stuck(pool, older_than_seconds)

The claim uses FOR UPDATE SKIP LOCKED inside a CTE so concurrent workers
can't double-execute a job. We only run one worker today, but this keeps us
honest if that ever changes.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Sentinel worker id. Populated from app.main at startup; kept module-level
# so call sites don't have to pass it through every layer.
WORKER_ID: str = "worker-unset"


async def enqueue(
    pool,
    lead_id: str,
    funnel_id: str,
    attempt_number: int,
    delay_seconds: int = 120,
) -> str:
    """Insert a pending retry row. Returns the job id."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO call_retry_jobs
                (lead_id, funnel_id, attempt_number, run_at)
            VALUES
                ($1, $2, $3, NOW() + make_interval(secs => $4))
            RETURNING id, run_at
            """,
            lead_id,
            funnel_id,
            attempt_number,
            delay_seconds,
        )
    logger.info(
        "call_retry enqueued: job=%s lead=%s attempt=%s run_at=%s",
        row["id"],
        lead_id,
        attempt_number,
        row["run_at"].isoformat(),
    )
    return str(row["id"])


async def claim_due(pool, worker_id: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Claim up to `limit` due retry jobs atomically.

    Uses SELECT ... FOR UPDATE SKIP LOCKED inside a CTE so concurrent
    workers can't grab the same row. The claimed rows are returned with
    status='in_progress' and the caller is responsible for eventually
    calling mark_done or mark_failed.
    """
    wid = worker_id or WORKER_ID
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH claimed AS (
                SELECT id
                  FROM call_retry_jobs
                 WHERE status = 'pending'
                   AND run_at <= NOW()
                 ORDER BY run_at
                 LIMIT $2
                 FOR UPDATE SKIP LOCKED
            )
            UPDATE call_retry_jobs AS j
               SET status     = 'in_progress',
                   locked_by  = $1,
                   locked_at  = NOW(),
                   updated_at = NOW()
              FROM claimed
             WHERE j.id = claimed.id
         RETURNING j.id, j.lead_id, j.funnel_id, j.attempt_number, j.run_at
            """,
            wid,
            limit,
        )
    return [dict(r) for r in rows]


async def mark_done(pool, job_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE call_retry_jobs
               SET status     = 'done',
                   updated_at = NOW(),
                   locked_by  = NULL,
                   locked_at  = NULL
             WHERE id = $1
            """,
            job_id,
        )


async def mark_failed(pool, job_id: str, error: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE call_retry_jobs
               SET status     = 'failed',
                   last_error = $2,
                   updated_at = NOW(),
                   locked_by  = NULL,
                   locked_at  = NULL
             WHERE id = $1
            """,
            job_id,
            error[:2000],  # bound length; full trace goes to Sentry
        )


async def recover_stuck(pool, older_than_seconds: int = 300) -> int:
    """Reset rows left 'in_progress' by a crashed worker back to 'pending'.

    Called on app startup. A row that's been 'in_progress' for longer than
    the longest plausible call (~5 min with Twilio ringing/connecting)
    almost certainly belongs to a dead process.
    """
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE call_retry_jobs
               SET status     = 'pending',
                   locked_by  = NULL,
                   locked_at  = NULL,
                   updated_at = NOW()
             WHERE status   = 'in_progress'
               AND locked_at < NOW() - make_interval(secs => $1)
            """,
            older_than_seconds,
        )
    # asyncpg returns "UPDATE N"
    try:
        count = int(result.split()[-1])
    except (ValueError, IndexError):
        count = 0
    if count:
        logger.warning("call_retry recovered %s stuck job(s) on startup", count)
    return count
