"""
Admin Ops API: operational triggers for testing and manual worker execution.
Not public — requires org-scoped admin auth.
"""

import json
import logging

import asyncpg
from fastapi import APIRouter, Depends

from app.core.auth import resolve_active_org_id
from app.database import get_db, pool as db_pool
from app.models.schemas import HandoffQueueItem, HandoffQueueResponse
from app.services.engagement_worker import process_due_engagement_steps

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ops/engagement/run")
async def run_engagement_worker(
    org_id: str = Depends(resolve_active_org_id),
):
    """
    Manually trigger processing of all due engagement steps.
    Returns a summary of what was processed.

    This is an admin-only operational trigger — not a public endpoint.
    """
    logger.info("Manual engagement worker run triggered by org=%s", org_id)
    summary = await process_due_engagement_steps(db_pool)
    return {"status": "ok", **summary}


@router.get("/ops/handoffs", response_model=HandoffQueueResponse)
async def get_handoff_queue(
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """
    Return leads that need human follow-up, org-scoped.
    Returns count + up to 5 most recent.
    """
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND needs_human = true",
        org_id,
    )

    rows = await conn.fetch(
        """
        SELECT id, answers_json, stage, handoff_reason, handoff_at
        FROM leads
        WHERE org_id = $1 AND needs_human = true
        ORDER BY handoff_at DESC NULLS LAST
        LIMIT 5
        """,
        org_id,
    )

    items = []
    for r in rows:
        answers = json.loads(r["answers_json"]) if isinstance(r["answers_json"], str) else r["answers_json"]
        items.append(HandoffQueueItem(
            id=r["id"],
            name=answers.get("name"),
            stage=r["stage"] or "new",
            handoff_reason=r["handoff_reason"],
            handoff_at=r["handoff_at"],
        ))

    return HandoffQueueResponse(count=int(count or 0), leads=items)
