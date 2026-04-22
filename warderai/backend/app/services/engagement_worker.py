"""
Engagement Worker V1.1: processes due engagement steps and fires delivery hooks.
Returns a summary dict of processed / sent / skipped / failed counts.
"""

import json
import logging
from datetime import datetime, timezone

import asyncpg

from app.services.engagement_service import log_engagement_event

logger = logging.getLogger(__name__)


async def process_due_engagement_steps(pool: asyncpg.Pool) -> dict:
    """
    Fetch and execute pending engagement steps whose scheduled_for <= now().
    Safe if Twilio / SMTP are not configured — marks as skipped_missing_config.
    Never crashes the caller if an individual step fails.

    Returns:
        {"processed": int, "sent": int, "skipped_missing_config": int, "failed": int}
    """
    summary = {"processed": 0, "sent": 0, "skipped_missing_config": 0, "failed": 0}

    try:
        async with pool.acquire() as conn:
            due_steps = await conn.fetch(
                """
                SELECT
                    es.id            AS step_id,
                    es.plan_id,
                    es.step_order,
                    es.channel,
                    es.action_type,
                    es.generated_content_json,
                    ep.lead_id,
                    ep.org_id,
                    ep.funnel_id,
                    ep.paused,
                    ep.status        AS plan_status
                FROM engagement_steps es
                JOIN engagement_plans ep ON ep.id = es.plan_id
                WHERE es.status = 'pending'
                  AND es.scheduled_for <= now()
                  AND ep.status = 'active'
                  AND ep.paused = false
                ORDER BY es.scheduled_for ASC
                LIMIT 100
                """
            )

            if not due_steps:
                return summary

            logger.info("Processing %d due engagement steps", len(due_steps))

            for step in due_steps:
                step_status = await _execute_step(conn, step)
                summary["processed"] += 1
                if step_status in summary:
                    summary[step_status] += 1

    except Exception as exc:
        logger.error("Engagement worker error: %s", exc)

    return summary


async def _execute_step(conn, step) -> str:
    """
    Execute a single engagement step. Catches all errors internally.
    Returns the final status string: 'sent' | 'skipped_missing_config' | 'failed'.
    """
    step_id  = str(step["step_id"])
    lead_id  = str(step["lead_id"])
    org_id   = str(step["org_id"])
    plan_id  = str(step["plan_id"])
    channel  = step["channel"]

    try:
        content = step["generated_content_json"]
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                content = {}
        content = content or {}

        # Load funnel for delivery config
        funnel = None
        if step["funnel_id"]:
            funnel = await conn.fetchrow(
                "SELECT * FROM funnels WHERE id = $1", str(step["funnel_id"])
            )

        # Load lead for delivery context
        lead = await conn.fetchrow(
            "SELECT * FROM leads WHERE id = $1", lead_id
        )
        if not lead:
            await _mark_step(conn, step_id, "failed")
            return "failed"

        lead_dict   = dict(lead)
        funnel_dict = dict(funnel) if funnel else {}

        # Attempt delivery
        if channel == "sms":
            status = await _send_sms(lead_dict, funnel_dict, content)
        elif channel == "email":
            status = await _send_email(lead_dict, funnel_dict, content)
        elif channel == "call":
            # Calls are not supported in V1 — explicitly skip
            logger.info(
                "Step %s (lead=%s, channel=call) skipped: call_not_supported_v1",
                step_id, lead_id,
            )
            status = "skipped_missing_config"
        else:
            status = "skipped_missing_config"

        now = datetime.now(timezone.utc)
        await conn.execute(
            """
            UPDATE engagement_steps
            SET status = $1, executed_at = $2
            WHERE id = $3
            """,
            status,
            now,
            step_id,
        )

        # Advance plan current_step
        await conn.execute(
            """
            UPDATE engagement_plans
            SET current_step = GREATEST(current_step, $1), updated_at = now()
            WHERE id = $2
            """,
            step["step_order"],
            plan_id,
        )

        # Log engagement event with enriched metadata
        event_type = f"{channel}_{'sent' if status == 'sent' else status}"
        snippet = None
        if channel == "sms":
            snippet = (content.get("sms_body") or "")[:160]
        elif channel == "email":
            snippet = content.get("email_subject") or ""

        await log_engagement_event(
            conn,
            lead_id=lead_id,
            org_id=org_id,
            channel=channel,
            event_type=event_type,
            direction="outbound",
            content=snippet,
            metadata={
                "step_id":    step_id,
                "step_order": step["step_order"],
                "plan_id":    plan_id,
                "status":     status,
            },
        )

        logger.info(
            "Step %s (lead=%s, channel=%s) -> %s", step_id, lead_id, channel, status
        )
        return status

    except Exception as exc:
        logger.error("Failed to execute step %s: %s", step_id, exc)
        try:
            await conn.execute(
                "UPDATE engagement_steps SET status = 'failed' WHERE id = $1", step_id
            )
        except Exception:
            pass
        return "failed"


async def _send_sms(lead_dict: dict, funnel_dict: dict, content: dict) -> str:
    """Send SMS via Twilio. Returns status string."""
    try:
        sms_body = content.get("sms_body")
        if not sms_body:
            return "skipped_missing_config"

        import os
        import httpx

        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
        from_number = funnel_dict.get("twilio_from_number") or ""

        answers = lead_dict.get("answers_json") or {}
        if isinstance(answers, str):
            try:
                answers = json.loads(answers)
            except Exception:
                answers = {}

        to_phone = answers.get("phone", "")

        if not account_sid or not auth_token or not from_number or not to_phone:
            return "skipped_missing_config"

        if to_phone.isdigit() and len(to_phone) == 10:
            to_phone = f"+1{to_phone}"
        elif not to_phone.startswith("+"):
            to_phone = f"+{to_phone}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data={"From": from_number, "To": to_phone, "Body": sms_body},
            )
            resp.raise_for_status()
        return "sent"

    except Exception as exc:
        logger.warning("SMS delivery failed: %s", exc)
        return "failed"


async def _send_email(lead_dict: dict, funnel_dict: dict, content: dict) -> str:
    """Send email via SMTP. Returns status string."""
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")
        smtp_from = os.getenv("SMTP_FROM", "")

        answers = lead_dict.get("answers_json") or {}
        if isinstance(answers, str):
            try:
                answers = json.loads(answers)
            except Exception:
                answers = {}

        to_email = answers.get("email", "")
        notification_emails = funnel_dict.get("notification_emails") or []

        recipients = [to_email] if to_email else notification_emails
        if not smtp_host or not smtp_from or not recipients:
            return "skipped_missing_config"

        subject = content.get("email_subject") or "Following up"
        body    = content.get("email_body") or ""

        msg = MIMEMultipart()
        msg["From"]    = smtp_from
        msg["To"]      = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_user and smtp_pass:
                server.starttls()
                server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, recipients, msg.as_string())

        return "sent"

    except Exception as exc:
        logger.warning("Email delivery failed: %s", exc)
        return "failed"


async def _mark_step(conn, step_id: str, status: str) -> None:
    try:
        await conn.execute(
            "UPDATE engagement_steps SET status = $1 WHERE id = $2", status, step_id
        )
    except Exception:
        pass
