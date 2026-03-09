"""
Admin Ops API: operational triggers for testing and manual worker execution.
Not public — requires org-scoped admin auth.
"""

import logging

from fastapi import APIRouter, Depends

from app.core.auth import resolve_active_org_id
from app.database import pool as db_pool
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
