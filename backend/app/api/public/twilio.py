"""Twilio webhook endpoints for bridge call flow."""
import asyncio
import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

router = APIRouter(tags=["twilio"])
logger = logging.getLogger(__name__)

TWILIO_WEBHOOK_SECRET = os.getenv("TWILIO_WEBHOOK_SECRET", "dev-webhook-secret")


def verify_secret(secret: str):
    """Validate webhook secret query parameter."""
    if secret != TWILIO_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")


@router.post("/twilio/rep-answer")
async def rep_answer(
    request: Request,
    lead_id: str = Query(...),
    secret: str = Query(...),
):
    """Called when rep answers the outbound call. Returns TwiML with gather prompt."""
    verify_secret(secret)

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="1" action="/public/twilio/rep-gather?lead_id={lead_id}&amp;secret={secret}" method="POST">
        <Say voice="alice">You have a new lead from SignalForge. Press 1 to connect.</Say>
    </Gather>
    <Say voice="alice">No input received. Goodbye.</Say>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/rep-gather")
async def rep_gather(
    request: Request,
    lead_id: str = Query(...),
    secret: str = Query(...),
):
    """Called after rep presses a digit. Bridges to lead if they pressed 1."""
    verify_secret(secret)

    form = await request.form()
    digits = form.get("Digits", "")

    pool = request.app.state.pool

    if digits == "1":
        # Look up lead phone from DB
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT answers_json FROM leads WHERE id = $1", lead_id
            )
            if not row:
                twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Say voice="alice">Lead not found. Goodbye.</Say><Hangup/></Response>"""
                return Response(content=twiml, media_type="application/xml")

            answers = row["answers_json"]
            if isinstance(answers, str):
                answers = json.loads(answers)
            lead_phone = answers.get("phone", "")

            if not lead_phone:
                twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Say voice="alice">No phone number on file. Goodbye.</Say><Hangup/></Response>"""
                return Response(content=twiml, media_type="application/xml")

            # Update lead status
            await conn.execute(
                "UPDATE leads SET contact_status = 'connected', last_contacted_at = $2 WHERE id = $1",
                lead_id,
                datetime.utcnow(),
            )

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Connecting you now.</Say>
    <Dial>{lead_phone}</Dial>
</Response>"""
        return Response(content=twiml, media_type="application/xml")
    else:
        # Rep declined
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE leads SET call_status = 'rep_declined' WHERE id = $1",
                lead_id,
            )

        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Say voice="alice">Goodbye.</Say><Hangup/></Response>"""
        return Response(content=twiml, media_type="application/xml")


@router.post("/twilio/status")
async def status_callback(
    request: Request,
    lead_id: str = Query(...),
    type: str = Query(...),
    secret: str = Query(...),
):
    """Twilio status callback - updates lead call/sms status in DB."""
    verify_secret(secret)

    form = await request.form()
    pool = request.app.state.pool

    if type == "call":
        call_status = form.get("CallStatus", "unknown")
        # Map Twilio status to our internal status
        status_map = {
            "completed": "completed",
            "busy": "busy",
            "no-answer": "no-answer",
            "failed": "failed",
            "canceled": "canceled",
        }
        mapped_status = status_map.get(call_status, call_status)

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE leads SET call_status = $2 WHERE id = $1",
                lead_id,
                mapped_status,
            )

            # Retry on failure statuses
            if mapped_status in ("failed", "no-answer", "busy"):
                row = await conn.fetchrow(
                    "SELECT * FROM leads WHERE id = $1", lead_id
                )
                if row and (row["call_attempts"] or 0) < 2:
                    lead_dict = dict(row)
                    answers = row["answers_json"]
                    if isinstance(answers, str):
                        lead_dict["answers_json"] = json.loads(answers)

                    # Get funnel for retry
                    funnel_row = await conn.fetchrow(
                        "SELECT * FROM funnels WHERE id = $1",
                        row["funnel_id"],
                    )
                    if funnel_row:
                        from app.services.call_service import retry_call

                        funnel_dict = dict(funnel_row)
                        asyncio.create_task(
                            retry_call(lead_id, lead_dict, funnel_dict, pool)
                        )

            # Auto text-back for missed calls
            if mapped_status in ("no-answer", "busy"):
                try:
                    from app.services.sequence_worker import _send_sequence_sms
                    lead_row = await conn.fetchrow(
                        "SELECT answers_json, funnel_id FROM leads WHERE id = $1", lead_id
                    )
                    if lead_row:
                        answers = lead_row["answers_json"]
                        if isinstance(answers, str):
                            import json as json_mod
                            answers = json_mod.loads(answers)
                        phone = answers.get("phone", "")
                        funnel_row = await conn.fetchrow(
                            "SELECT twilio_from_number FROM funnels WHERE id = $1", lead_row["funnel_id"]
                        )
                        from_num = funnel_row["twilio_from_number"] if funnel_row else None
                        if phone and from_num:
                            sms_status = await _send_sequence_sms(
                                phone,
                                "Sorry we missed you. Reply YES and we'll call you back.",
                                from_num,
                            )
                            await conn.execute(
                                "UPDATE leads SET sms_status = $1 WHERE id = $2",
                                f"textback_{sms_status}", lead_id,
                            )
                except Exception as e:
                    logger.exception("Missed call text-back failed: %s", e)

        logger.info("Call status for lead %s: %s", lead_id, mapped_status)

    elif type == "sms":
        sms_status = form.get("SmsStatus", form.get("MessageStatus", "unknown"))
        status_map = {
            "sent": "sent",
            "delivered": "delivered",
            "undelivered": "undelivered",
            "failed": "failed",
        }
        mapped_status = status_map.get(sms_status, sms_status)

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE leads SET sms_status = $2 WHERE id = $1",
                lead_id,
                mapped_status,
            )

        logger.info("SMS status for lead %s: %s", lead_id, mapped_status)

    return Response(content="<Response/>", media_type="application/xml")
