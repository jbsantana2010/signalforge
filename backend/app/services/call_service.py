"""Twilio bridge call service - connects rep to lead via phone bridge."""
import asyncio
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


async def start_rep_call(lead: dict, funnel: dict, pool) -> str:
    """
    Initiate a bridge call: call the rep first, then bridge to lead.

    Returns: "initiated", "skipped_missing_config", "skipped_outside_hours", or "failed"
    """
    # 1. Check working hours (server time)
    current_hour = datetime.now().hour
    start_hour = funnel.get("working_hours_start")
    end_hour = funnel.get("working_hours_end")
    if start_hour is not None and end_hour is not None:
        if not (start_hour <= current_hour < end_hour):
            logger.info("Outside working hours (%s-%s), current=%s", start_hour, end_hour, current_hour)
            return "skipped_outside_hours"

    # 2. Check Twilio credentials
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        logger.warning("Twilio credentials not configured")
        return "skipped_missing_config"

    # 3. Check funnel phone config
    rep_phone = funnel.get("rep_phone_number")
    from_number = funnel.get("twilio_from_number")
    if not rep_phone or not from_number:
        logger.warning("Funnel missing rep_phone_number or twilio_from_number")
        return "skipped_missing_config"

    # 4. Build webhook URLs and create outbound call
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    webhook_secret = os.getenv("TWILIO_WEBHOOK_SECRET", "dev-webhook-secret")
    lead_id = str(lead["id"])

    webhook_url = (
        f"{base_url}/public/twilio/rep-answer"
        f"?lead_id={lead_id}&secret={webhook_secret}"
    )
    status_url = (
        f"{base_url}/public/twilio/status"
        f"?lead_id={lead_id}&type=call&secret={webhook_secret}"
    )

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        call = client.calls.create(
            to=rep_phone,
            from_=from_number,
            url=webhook_url,
            status_callback=status_url,
            status_callback_event=["completed", "busy", "no-answer", "failed"],
        )
        logger.info("Twilio call initiated: sid=%s lead_id=%s", call.sid, lead_id)
        return "initiated"
    except Exception:
        logger.exception("Failed to initiate Twilio call for lead %s", lead_id)
        return "failed"


async def retry_call(lead_id: str, lead: dict, funnel: dict, pool):
    """
    If call_attempts < 2, wait 2 minutes then retry.
    Updates call_attempts and call_status in DB.
    """
    attempts = lead.get("call_attempts", 0)
    if attempts >= 2:
        logger.info("Max retry attempts reached for lead %s", lead_id)
        return

    logger.info("Scheduling retry for lead %s in 120s (attempt %s)", lead_id, attempts + 1)
    await asyncio.sleep(120)

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE leads SET call_attempts = call_attempts + 1, call_status = 'retrying' WHERE id = $1",
            lead_id,
        )

        # Re-fetch lead with updated attempts
        row = await conn.fetchrow("SELECT * FROM leads WHERE id = $1", lead_id)
        if not row:
            return
        updated_lead = dict(row)
        answers = row["answers_json"]
        if isinstance(answers, str):
            updated_lead["answers_json"] = json.loads(answers)

    status = await start_rep_call(updated_lead, funnel, pool)
    logger.info("Retry call result for lead %s: %s", lead_id, status)
