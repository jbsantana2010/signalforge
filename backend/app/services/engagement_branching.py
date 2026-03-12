"""
Engagement branching service — applies deterministic reply-driven branching rules
to active engagement plans.

Called after inbound SMS classification to adjust plan behavior.
No AI. No external calls. Deterministic only.
"""

import logging
from datetime import datetime, timedelta, timezone

import asyncpg

from app.services.engagement_service import log_engagement_event

logger = logging.getLogger(__name__)


async def apply_reply_branching(
    conn: asyncpg.Connection,
    lead_id: str,
    org_id: str,
    classification: str,
    inbound_message_id: str | None = None,
) -> None:
    """
    Apply branching rules based on reply classification.

    Classification → behaviour:
      interested     — keep plan active, log branch_interested
      price          — keep plan active, log branch_price
      info           — keep plan active, log branch_info
      timing         — keep plan active, reschedule next pending SMS +24h, log branch_timing
      not_interested — pause plan, cancel pending steps, log branch_not_interested
      human_needed   — pause plan, cancel pending steps, mark lead needs_human, log handoff_required
      unknown        — same as human_needed
    """
    metadata: dict = {
        "classification": classification,
        "inbound_message_id": inbound_message_id,
    }

    try:
        if classification == "interested":
            await log_engagement_event(
                conn, lead_id=lead_id, org_id=org_id,
                channel="system", event_type="branch_interested",
                direction="system", content=None, metadata=metadata,
            )

        elif classification == "price":
            await log_engagement_event(
                conn, lead_id=lead_id, org_id=org_id,
                channel="system", event_type="branch_price",
                direction="system", content=None, metadata=metadata,
            )

        elif classification == "info":
            await log_engagement_event(
                conn, lead_id=lead_id, org_id=org_id,
                channel="system", event_type="branch_info",
                direction="system", content=None, metadata=metadata,
            )

        elif classification == "timing":
            await _reschedule_next_pending_sms(conn, lead_id)
            await log_engagement_event(
                conn, lead_id=lead_id, org_id=org_id,
                channel="system", event_type="branch_timing",
                direction="system", content=None, metadata=metadata,
            )

        elif classification == "not_interested":
            await _pause_and_cancel(conn, lead_id)
            await log_engagement_event(
                conn, lead_id=lead_id, org_id=org_id,
                channel="system", event_type="branch_not_interested",
                direction="system", content=None, metadata=metadata,
            )

        elif classification in ("human_needed", "unknown"):
            await _pause_and_cancel(conn, lead_id)
            await conn.execute(
                """
                UPDATE leads
                SET needs_human = true,
                    handoff_reason = 'reply_requires_human',
                    handoff_at = now()
                WHERE id = $1
                """,
                lead_id,
            )
            await log_engagement_event(
                conn, lead_id=lead_id, org_id=org_id,
                channel="system", event_type="handoff_required",
                direction="system", content=None, metadata=metadata,
            )
            logger.info(
                "Lead %s marked needs_human — classification: %s", lead_id, classification
            )

        else:
            logger.warning(
                "Unrecognised classification '%s' for lead %s — no branching applied",
                classification, lead_id,
            )

    except Exception as exc:
        logger.error(
            "Branching failed for lead %s (classification=%s): %s",
            lead_id, classification, exc,
        )


async def _pause_and_cancel(conn: asyncpg.Connection, lead_id: str) -> None:
    """Pause the active engagement plan and cancel all pending steps."""
    try:
        await conn.execute(
            """
            UPDATE engagement_plans
            SET paused = true,
                escalation_reason = 'reply_requires_human',
                updated_at = now()
            WHERE lead_id = $1 AND status = 'active'
            """,
            lead_id,
        )
        await conn.execute(
            """
            UPDATE engagement_steps
            SET status = 'cancelled'
            WHERE plan_id IN (
                SELECT id FROM engagement_plans
                WHERE lead_id = $1 AND status = 'active'
            )
            AND status = 'pending'
            """,
            lead_id,
        )
    except Exception as exc:
        logger.error("Failed to pause/cancel plan for lead %s: %s", lead_id, exc)


async def _reschedule_next_pending_sms(conn: asyncpg.Connection, lead_id: str) -> None:
    """Reschedule the next pending SMS engagement step to 24 hours from now."""
    try:
        new_time = datetime.now(timezone.utc) + timedelta(hours=24)
        await conn.execute(
            """
            UPDATE engagement_steps
            SET scheduled_for = $1
            WHERE id = (
                SELECT es.id
                FROM engagement_steps es
                JOIN engagement_plans ep ON ep.id = es.plan_id
                WHERE ep.lead_id = $2
                  AND ep.status = 'active'
                  AND es.channel = 'sms'
                  AND es.status = 'pending'
                ORDER BY es.step_order ASC
                LIMIT 1
            )
            """,
            new_time,
            lead_id,
        )
    except Exception as exc:
        logger.error("Failed to reschedule SMS step for lead %s: %s", lead_id, exc)
