"""
Inbound SMS webhook — receives lead replies, classifies them, logs events,
and applies engagement branching rules.

POST /public/inbound/sms
Human-in-the-loop: DOES NOT auto-send replies.
"""

import json
import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.services.reply_classifier import classify_reply
from app.services.engagement_service import log_engagement_event
from app.services.engagement_branching import apply_reply_branching

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

    return {
        "status": "ok",
        "classification": classification,
        "suggested_response": suggested_response,
    }
