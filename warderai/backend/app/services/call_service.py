"""Twilio bridge call service - connects rep to lead via phone bridge."""
import json
import logging
import os
from datetime import datetime

from app.services import call_retry_queue

logger = logging.getLogger(__name__)


async def start_rep_call(lead: dict, funnel: dict, pool) -> str:
    """Initiate a bridge call: call the rep first, then bridge to lead.

    Returns: "initiated", "skipped_missing_config", "skipped_outside_hours", or "failed"
    """
    current_hour = datetime.now().hour
    start_hour = funnel.get("working_hours_start")
    end_hour = funnel.get("working_hours_end")
    if start_hour is not None and end_hour is not None:
        if not (start_hour <= current_hour < end_hour):
            logger.info("Outside working hours (%s-%s), current=%s",
                        start_hour, end_hour, current_hour)
            return "skipped_outside_hours"

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        logger.warning("Twilio credentials not configured")
        return "skipped_missing_config"

    rep_phone = funnel.get("rep_phone_number")
    from_number = funnel.get("twilio_from_number")
    if not rep_phone or not from_number:
        logger.warning("Funnel missing rep_phone_number or twilio_from_number")
        return "skipped_missing_config"

    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    webhook_secret = os.getenv("TWILIO_WEBHOOK_SECRET", "dev-webhook-secret")
    lead_id = str(lead["id"])

    webhook_url = (f"{base_url}/public/twilio/rep-answer"
                   f"?lead_id={lead_id}&secret={webhook_secret}")
    status_url = (f"{base_url}/public/twilio/status"
                  f"?lead_id={lead_id}&type=call&secret={webhook_secret}")

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


async def schedule_retry(lead_id, funnel_id, current_attempts, pool, delay_seconds=120):
    """Persist a retry intent so it survives server restarts.

    Replaces the prior asyncio.sleep(120) in-process retry. The actual
    retry is executed by run_due_retries() on the APScheduler tick.

    Returns the job id (str), or None if max attempts already reached.
    """
    if current_attempts >= 2:
        logger.info("Max retry attempts reached for lead %s; not enqueuing", lead_id)
        return None

    next_attempt = current_attempts + 1
    job_id = await call_retry_queue.enqueue(
        pool=pool,
        lead_id=lead_id,
        funnel_id=funnel_id,
        attempt_number=next_attempt,
        delay_seconds=delay_seconds,
    )
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE leads SET call_status = 'retry_scheduled' WHERE id = $1",
            lead_id,
        )
    return job_id


async def _execute_retry(job, pool):
    """Execute a single claimed retry job.

    Called by run_due_retries. Assumes the row is already 'in_progress'.
    """
    job_id = str(job["id"])
    lead_id = str(job["lead_id"])
    funnel_id = str(job["funnel_id"])

    try:
        async with pool.acquire() as conn:
            lead_row = await conn.fetchrow("SELECT * FROM leads WHERE id = $1", lead_id)
            if not lead_row:
                logger.warning("call_retry lead %s disappeared; marking done", lead_id)
                await call_retry_queue.mark_done(pool, job_id)
                return

            funnel_row = await conn.fetchrow(
                "SELECT * FROM funnels WHERE id = $1", funnel_id
            )
            if not funnel_row:
                logger.warning("call_retry funnel %s disappeared; marking failed", funnel_id)
                await call_retry_queue.mark_failed(pool, job_id, "funnel_missing")
                return

            await conn.execute(
                "UPDATE leads SET call_attempts = call_attempts + 1, "
                "call_status = 'retrying' WHERE id = $1",
                lead_id,
            )
            lead_dict = dict(lead_row)
            lead_dict["call_attempts"] = (lead_row["call_attempts"] or 0) + 1
            if isinstance(lead_dict.get("answers_json"), str):
                lead_dict["answers_json"] = json.loads(lead_dict["answers_json"])
            funnel_dict = dict(funnel_row)

        status = await start_rep_call(lead_dict, funnel_dict, pool)
        logger.info("call_retry fired: job=%s lead=%s result=%s", job_id, lead_id, status)

        if status in ("initiated", "skipped_outside_hours", "skipped_missing_config"):
            await call_retry_queue.mark_done(pool, job_id)
        else:
            await call_retry_queue.mark_failed(pool, job_id, "start_rep_call=" + status)
    except Exception as exc:
        logger.exception("call_retry job %s crashed", job_id)
        await call_retry_queue.mark_failed(pool, job_id, repr(exc))


async def run_due_retries(pool):
    """Claim and execute any due retries. Called on the APScheduler tick."""
    recovered = await call_retry_queue.recover_stuck(pool)

    jobs = await call_retry_queue.claim_due(pool, limit=10)
    if not jobs:
        return {"recovered": recovered, "processed": 0}

    for job in jobs:
        await _execute_retry(job, pool)

    return {"recovered": recovered, "processed": len(jobs)}


# Backwards-compat shim; remove once every callsite is on schedule_retry.
async def retry_call(lead_id, lead, funnel, pool):
    current_attempts = lead.get("call_attempts", 0)
    funnel_id = str(lead.get("funnel_id") or funnel.get("id"))
    await schedule_retry(
        lead_id=lead_id,
        funnel_id=funnel_id,
        current_attempts=current_attempts,
        pool=pool,
    )
