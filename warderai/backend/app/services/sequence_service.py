"""SMS follow-up sequence engine."""
import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def schedule_sequences(lead_id: str, funnel: dict, conn):
    """Create lead_sequences rows for each step in funnel.sequence_config."""
    if not funnel.get("sequence_enabled"):
        return

    config = funnel.get("sequence_config")
    if not config:
        return

    if isinstance(config, str):
        config = json.loads(config)

    steps = config.get("steps", [])
    if not steps:
        return

    now = datetime.now(timezone.utc)
    for i, step in enumerate(steps):
        delay = step.get("delay_minutes", 0)
        message = step.get("message", "")
        scheduled_at = now + timedelta(minutes=delay)

        await conn.execute(
            """
            INSERT INTO lead_sequences (lead_id, step, scheduled_at, status, message)
            VALUES ($1, $2, $3, $4, $5)
            """,
            lead_id,
            i + 1,
            scheduled_at,
            "pending",
            message,
        )

    logger.info("Scheduled %d sequence steps for lead %s", len(steps), lead_id)
