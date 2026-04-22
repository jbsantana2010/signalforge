"""
Inbound SMS webhook — receives lead replies, classifies them, logs events,
applies engagement branching rules, and auto-sends suggested replies for
positive/neutral intent (interested, price, info, timing).

POST /public/inbound/sms
"""

import json
import logging
import os

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.services.reply_classifier import classify_reply
from app.services.engagement_service import log_engagement_event
from app.services.engagement_branching import apply_reply_branching

# Classifications that trigger an automatic SMS reply to the lead
AUTO_REPLY_CLASSIFICATIONS = {"interested", "price", "info", "timing"}

logger = logging.getLogger(__name__)

router = APIRouter()


class InboundSmsPayload(BaseModel):
    # Twilio-style but flexible — accept both "From" (Twilio) and "from"
    # We normalise via aliases below
    from_number: str | None = None
    body: str | None = None

    # Support Twilio's exact PascalCase field names too
    From: str | None = None
    Body: str | None = None

    def get_from(self) -> str | None:
        return self.from_number or self.From

    def get_body(self) -> str | None:
        return self.body or self.Body


@router.post("/inbound/sms")
async def inbound_sms(
    payload: InboundSmsPayload,
    conn: asyncpg.Connection = Depends(get_db),
):
    """
    Receive an inbound SMS reply from a lead.

    1. Identify lead by phone number
    2. Classify the reply
    3. Create inbound_messages row
    4. Log sms_reply engagement event
    5. Apply branching rules based on classification
    """
    from_number = payload.get_from()
    message_body = payload.get_body()

    if not from_number or not message_body:
        raise HTTPException(status_code=422, detail="from/body are required")

    # Normalise phone: strip non-digits for matching
    digits_only = "".join(c for c in from_number if c.isdigit())

    # Look up lead by phone — match last 10 digits to handle +1 prefix variation
    lead_row = await conn.fetchrow(
        """
        SELECT l.id, l.org_id
        FROM leads l
        WHERE
            -- exact match
            answers_json->>'phone' = $1
            OR answers_json->>'phone' = $2
            -- suffix match (last 10 digits)
            OR right(regexp_replace(answers_json->>'phone', '[^0-9]', '', 'g'), 10)
               = right($3, 10)
        ORDER BY l.created_at DESC
        LIMIT 1
        """,
        from_number,
        digits_only,
        digits_only,
    )

    if not lead_row:
        logger.warning("Inbound SMS from unknown number: %s", from_number)
        raise HTTPException(status_code=404, detail="Lead not found for this phone number")

    lead_id = str(lead_row["id"])
    org_id = str(lead_row["org_id"])

    # Classify the reply
    result = classify_reply(message_body)
    classification = result["classification"]
    suggested_response = result["suggested_response"]

    # Insert inbound_messages row
    inbound_id = await conn.fetchval(
        """
        INSERT INTO inbound_messages
            (lead_id, org_id, channel, message_body, classification, suggested_response, metadata_json)
        VALUES ($1, $2, 'sms', $3, $4, $5, $6)
        RETURNING id
        """,
        lead_id,
        org_id,
        message_body,
        classification,
        suggested_response,
        json.dumps({"from_number": from_number}),
    )

    # Log engagement event
    await log_engagement_event(
        conn,
        lead_id=lead_id,
        org_id=org_id,
        channel="sms",
        event_type="sms_reply",
        direction="inbound",
        content=message_body,
        metadata={
            "inbound_message_id": str(inbound_id),
            "classification": classification,
            "suggested_response": suggested_response,
            "from_number": from_number,
        },
    )

    # Apply branching rules based on classification
    await apply_reply_branching(
        conn,
        lead_id=lead_id,
        org_id=org_id,
        classification=classification,
        inbound_message_id=str(inbound_id),
    )

    # Auto-send suggested reply for positive/neutral intent
    auto_reply_sent = False
    if classification in AUTO_REPLY_CLASSIFICATIONS and suggested_response:
        auto_reply_sent = await _auto_send_sms_reply(
            conn=conn,
            lead_id=lead_id,
            org_id=org_id,
            to_number=from_number,
            message_body=suggested_response,
        )

    return {
        "status": "ok",
        "classification": classification,
        "suggested_response": suggested_response,
        "auto_reply_sent": auto_reply_sent,
    }


async def _auto_send_sms_reply(
    conn: asyncpg.Connection,
    lead_id: str,
    org_id: str,
    to_number: str,
    message_body: str,
) -> bool:
    """
    Send an automatic SMS reply to a lead using the funnel's Twilio from-number.
    Fails gracefully — logs warning but never raises.
    Returns True if the message was sent successfully.
    """
    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
        if not account_sid or not auth_token:
            logger.warning("Auto-reply skipped: Twilio credentials not configured (lead=%s)", lead_id)
            return False

        # Look up the funnel's twilio_from_number via the lead
        row = await conn.fetchrow(
            """
            SELECT f.twilio_from_number
            FROM leads l
            JOIN funnels f ON f.id = l.funnel_id
            WHERE l.id = $1
            """,
            lead_id,
        )
        from_number = row["twilio_from_number"] if row else None
        if not from_number:
            logger.warning("Auto-reply skipped: no twilio_from_number for lead %s", lead_id)
            return False

        # Normalise destination number
        digits = "".join(c for c in to_number if c.isdigit())
        if len(digits) == 10:
            to_phone = f"+1{digits}"
        elif len(digits) == 11 and digits.startswith("1"):
            to_phone = f"+{digits}"
        else:
            to_phone = to_number if to_number.startswith("+") else f"+{digits}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data={"From": from_number, "To": to_phone, "Body": message_body},
            )
            resp.raise_for_status()

        logger.info("Auto-reply sent to lead %s (%s)", lead_id, to_phone)

        await log_engagement_event(
            conn,
            lead_id=lead_id,
            org_id=org_id,
            channel="sms",
            event_type="sms_auto_reply_sent",
            direction="outbound",
            content=message_body,
            metadata={"to_number": to_phone, "trigger": "auto_reply"},
        )
        return True

    except Exception as exc:
        logger.warning("Auto-reply failed for lead %s: %s", lead_id, exc)
        return False
