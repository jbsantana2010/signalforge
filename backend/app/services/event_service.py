"""Automation event logging."""

import json
import logging

logger = logging.getLogger(__name__)


async def log_event(conn, org_id, lead_id, event_type: str, status: str, detail: dict | None = None):
    """Insert an automation event. Never throws — logs silently on failure."""
    try:
        await conn.execute(
            """INSERT INTO automation_events (org_id, lead_id, event_type, status, detail_json)
               VALUES ($1, $2, $3, $4, $5)""",
            org_id,
            lead_id,
            event_type,
            status,
            json.dumps(detail) if detail else None,
        )
    except Exception as exc:
        logger.warning("Failed to log event %s for lead %s: %s", event_type, lead_id, exc)
