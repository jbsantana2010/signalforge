"""Tests for the persisted call-retry flow (BE-01).

These tests mock asyncpg so they can run without a live Postgres. They
prove the correctness properties we care about:

  1. schedule_retry respects the max-attempts cap.
  2. schedule_retry writes a pending row and marks the lead as retry_scheduled.
  3. run_due_retries calls recover_stuck before claiming.
  4. A crash mid-execute leaves the job marked failed (not silently dropped).

What these tests do NOT cover (intentionally — needs a live DB):

  - The SKIP LOCKED contention behavior under concurrent workers.
  - The actual SQL CTE syntax (caught by the migration run in seed.py).

Those belong in an integration suite that spins up Postgres. For pilot we
rely on the single-worker invariant plus the dry-run in QA-02.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services import call_service


class _FakePool:
    """Minimal stand-in for an asyncpg pool whose acquire() returns a mock conn."""

    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        pool = self

        class _Ctx:
            async def __aenter__(self_inner):
                return pool._conn

            async def __aexit__(self_inner, *args):
                return False

        return _Ctx()


@pytest.fixture
def fake_pool():
    conn = AsyncMock()
    return _FakePool(conn), conn


@pytest.mark.asyncio
async def test_schedule_retry_caps_at_max_attempts(fake_pool):
    """At attempts >= 2, schedule_retry must return None and not enqueue."""
    pool, conn = fake_pool
    lead_id = str(uuid4())
    funnel_id = str(uuid4())

    with patch("app.services.call_service.call_retry_queue.enqueue", new=AsyncMock()) as mock_enqueue:
        result = await call_service.schedule_retry(
            lead_id=lead_id,
            funnel_id=funnel_id,
            current_attempts=2,
            pool=pool,
        )

    assert result is None
    mock_enqueue.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_retry_enqueues_and_marks_lead(fake_pool):
    """Under the cap: enqueue a row and flip lead.call_status to retry_scheduled."""
    pool, conn = fake_pool
    lead_id = str(uuid4())
    funnel_id = str(uuid4())

    with patch(
        "app.services.call_service.call_retry_queue.enqueue",
        new=AsyncMock(return_value="job-123"),
    ) as mock_enqueue:
        result = await call_service.schedule_retry(
            lead_id=lead_id,
            funnel_id=funnel_id,
            current_attempts=0,
            pool=pool,
        )

    assert result == "job-123"
    mock_enqueue.assert_awaited_once()
    # attempt_number passed in is current + 1
    _, kwargs = mock_enqueue.await_args
    assert kwargs["attempt_number"] == 1
    assert kwargs["delay_seconds"] == 120

    # Lead marked as scheduled so the admin UI shows the right state.
    conn.execute.assert_awaited()
    args, _ = conn.execute.await_args
    assert "retry_scheduled" in args[0]
    assert args[1] == lead_id


@pytest.mark.asyncio
async def test_run_due_retries_recovers_before_claiming(fake_pool):
    """Startup recovery MUST run before claim so a crashed-worker row
    gets back into the pending pool on the same tick."""
    pool, _ = fake_pool

    call_order: list[str] = []

    async def fake_recover(p, **kwargs):
        call_order.append("recover")
        return 0

    async def fake_claim(p, worker_id=None, limit=10):
        call_order.append("claim")
        return []  # nothing due on this tick

    with patch("app.services.call_service.call_retry_queue.recover_stuck", new=fake_recover), \
         patch("app.services.call_service.call_retry_queue.claim_due", new=fake_claim):
        result = await call_service.run_due_retries(pool)

    assert call_order == ["recover", "claim"]
    assert result == {"recovered": 0, "processed": 0}


@pytest.mark.asyncio
async def test_execute_retry_marks_failed_on_crash(fake_pool):
    """If _execute_retry raises, the job must be marked failed — never
    silently dropped. Otherwise a crashed job stays locked forever and
    the only way out is startup recovery."""
    pool, conn = fake_pool

    # fetchrow raises on first call — simulates a DB hiccup mid-execute.
    conn.fetchrow = AsyncMock(side_effect=RuntimeError("db hiccup"))

    mark_failed = AsyncMock()
    with patch("app.services.call_service.call_retry_queue.mark_failed", new=mark_failed):
        job = {
            "id": uuid4(),
            "lead_id": uuid4(),
            "funnel_id": uuid4(),
            "attempt_number": 1,
            "run_at": None,
        }
        await call_service._execute_retry(job, pool)

    mark_failed.assert_awaited_once()
    args, _ = mark_failed.await_args
    # (pool, job_id, error_string)
    assert "db hiccup" in args[2]
