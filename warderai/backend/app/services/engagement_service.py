"""
Engagement Engine V1: creates follow-up plans and logs engagement events.
No AI calls in this version — deterministic templates only.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _build_default_step_content(lead_data: dict) -> dict:
    """
    Build deterministic template content from lead context.
    Returns dict with sms_body, email_subject, email_body keyed per step.
    """
    answers = lead_data.get("answers_json") or {}
    if isinstance(answers, str):
        try:
            answers = json.loads(answers)
        except Exception:
            answers = {}

    name = answers.get("name") or "there"
    service = answers.get("service") or "your inquiry"

    return {
        1: {
            "channel": "sms",
            "template_key": "intro_sms_1",
            "sms_body": (
                f"Hi {name}, thanks for reaching out about {service}! "
                "We'll be in touch shortly. Reply STOP to opt out."
            ),
        },
        2: {
            "channel": "email",
            "template_key": "intro_email_1",
            "email_subject": f"Following up on your {service} inquiry",
            "email_body": (
                f"Hi {name},\n\n"
                f"Thanks for your interest in {service}. "
                "Our team has received your request and will reach out soon.\n\n"
                "Best regards,\nThe Team"
            ),
        },
        3: {
            "channel": "sms",
            "template_key": "followup_sms_1",
            "sms_body": (
                f"Hi {name}, just checking in on your {service} request. "
                "Any questions? Reply here."
            ),
        },
        4: {
            "channel": "email",
            "template_key": "followup_email_1",
            "email_subject": f"Still interested in {service}?",
            "email_body": (
                f"Hi {name},\n\n"
                f"We noticed you haven't had a chance to connect yet regarding {service}. "
                "We'd love to help — reply to this email or give us a call.\n\n"
                "Best regards,\nThe Team"
            ),
        },
    }


async def log_engagement_event(
    conn,
    lead_id: str,
    org_id: str,
    channel: str,
    event_type: str,
    direction: str,
    content: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Insert an engagement event. Never throws."""
    try:
        await conn.execute(
            """
            INSERT INTO engagement_events
                (lead_id, org_id, channel, event_type, direction, content, metadata_json)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            lead_id,
            org_id,
            channel,
            event_type,
            direction,
            content,
            json.dumps(metadata) if metadata else None,
        )
    except Exception as exc:
        logger.warning(
            "Failed to log engagement event %s for lead %s: %s", event_type, lead_id, exc
        )


async def create_engagement_plan(
    conn,
    lead_id: str,
    org_id: str,
    funnel_id: str | None,
    lead_data: dict,
) -> dict | None:
    """
    Create an engagement plan + default V1 steps for a lead.
    If an active plan already exists, return it without creating a duplicate.
    Returns the plan row as a dict, or None on error.
    """
    try:
        # Check for existing active plan
        existing = await conn.fetchrow(
            "SELECT id FROM engagement_plans WHERE lead_id = $1 AND status = 'active'",
            lead_id,
        )
        if existing:
            logger.info("Engagement plan already exists for lead %s", lead_id)
            return {"id": str(existing["id"]), "existing": True}

        # Create plan
        plan_id = await conn.fetchval(
            """
            INSERT INTO engagement_plans (lead_id, org_id, funnel_id, status)
            VALUES ($1, $2, $3, 'active')
            RETURNING id
            """,
            lead_id,
            org_id,
            funnel_id,
        )

        now = datetime.now(timezone.utc)

        # Default V1 step schedule
        step_schedule = [
            (1, "sms",   now + timedelta(seconds=30)),
            (2, "email", now + timedelta(minutes=2)),
            (3, "sms",   now + timedelta(hours=1)),
            (4, "email", now + timedelta(hours=24)),
        ]

        content_map = _build_default_step_content(lead_data)

        for step_order, channel, scheduled_for in step_schedule:
            content = content_map.get(step_order, {})
            await conn.execute(
                """
                INSERT INTO engagement_steps
                    (plan_id, step_order, channel, action_type,
                     scheduled_for, status, template_key, generated_content_json)
                VALUES ($1, $2, $3, 'send', $4, 'pending', $5, $6)
                """,
                str(plan_id),
                step_order,
                channel,
                scheduled_for,
                content.get("template_key"),
                json.dumps(content),
            )

        logger.info(
            "Created engagement plan %s with %d steps for lead %s",
            plan_id, len(step_schedule), lead_id,
        )

        await log_engagement_event(
            conn,
            lead_id=lead_id,
            org_id=org_id,
            channel="system",
            event_type="plan_created",
            direction="system",
            metadata={"plan_id": str(plan_id), "steps": len(step_schedule)},
        )

        return {"id": str(plan_id), "existing": False}

    except Exception as exc:
        logger.error("Failed to create engagement plan for lead %s: %s", lead_id, exc)
        return None
