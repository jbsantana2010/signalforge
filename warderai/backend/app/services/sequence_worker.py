"""Processes due SMS sequences."""
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def process_due_sequences(pool):
    """Query unsent rows where scheduled_at <= now, send SMS, update status."""
    from app.services.notification_service import send_sms

    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ls.id, ls.lead_id, ls.step, ls.message,
                   l.answers_json, l.funnel_id,
                   f.twilio_from_number
            FROM lead_sequences ls
            JOIN leads l ON l.id = ls.lead_id
            JOIN funnels f ON f.id = l.funnel_id
            WHERE ls.status = 'pending' AND ls.scheduled_at <= $1
            ORDER BY ls.scheduled_at
            LIMIT 50
            """,
            now,
        )

        for row in rows:
            answers = row["answers_json"]
            if isinstance(answers, str):
                answers = json.loads(answers)

            phone = answers.get("phone", "")
            if not phone:
                await conn.execute(
                    "UPDATE lead_sequences SET status = 'skipped', sent_at = $1 WHERE id = $2",
                    now, row["id"],
                )
                continue

            # Build a lead-like dict and funnel-like dict for send_sms
            # But we want to send the custom message, not the default template
            # So we'll call _send_sms_raw directly
            status = await _send_sequence_sms(
                phone, row["message"], row["twilio_from_number"]
            )

            await conn.execute(
                "UPDATE lead_sequences SET status = $1, sent_at = $2 WHERE id = $3",
                status, now, row["id"],
            )

        logger.info("Processed %d due sequences", len(rows))


async def _send_sequence_sms(phone: str, message: str, from_number: str | None) -> str:
    """Send a single SMS with custom message body."""
    import os

    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")

    if not account_sid or not auth_token or not from_number or not phone:
        return "skipped_missing_config"

    # Format phone
    if phone.isdigit() and len(phone) == 10:
        phone = f"+1{phone}"
    elif not phone.startswith("+"):
        phone = f"+{phone}"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data={"From": from_number, "To": phone, "Body": message},
            )
            resp.raise_for_status()
            return "sent"
    except Exception as e:
        logger.error("Sequence SMS failed: %s", e)
        return "failed"
