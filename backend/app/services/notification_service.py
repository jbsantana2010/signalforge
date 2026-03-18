"""
Notification service: sends email and SMS notifications for new leads.
Also provides lightweight handoff notification via engagement_event logging.
"""

import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import asyncpg

logger = logging.getLogger(__name__)


async def notify_handoff_required(
    conn: asyncpg.Connection,
    lead_id: str,
    org_id: str,
    owner_email: str | None,
    reason: str,
) -> None:
    """
    Log a rep_notified engagement_event.
    Does not send any real notification yet — event-based only.
    Never throws.
    """
    from app.services.engagement_service import log_engagement_event
    try:
        await log_engagement_event(
            conn,
            lead_id=lead_id,
            org_id=org_id,
            channel="system",
            event_type="rep_notified",
            direction="system",
            content=None,
            metadata={
                "owner_email": owner_email,
                "reason": reason,
            },
        )
        logger.info(
            "rep_notified event logged for lead %s — owner=%s", lead_id, owner_email
        )
    except Exception as exc:
        logger.error(
            "notify_handoff_required failed for lead %s: %s", lead_id, exc
        )


async def send_email(lead: dict, funnel: dict) -> str:
    """
    Send email notification to funnel.notification_emails using SMTP config.
    Returns status: "sent", "failed", "skipped_missing_config"
    """
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", "")

    notification_emails = funnel.get("notification_emails") or []

    if not smtp_host or not smtp_from or not notification_emails:
        return "skipped_missing_config"

    answers = lead.get("answers_json", {})
    if isinstance(answers, str):
        answers = json.loads(answers)

    name = answers.get("name", "Unknown")
    phone = answers.get("phone", "N/A")
    service = answers.get("service", "N/A")
    lead_id = lead.get("id", "N/A")

    subject = f"New Lead: {name} - {service}"
    body = (
        f"New lead submitted:\n\n"
        f"Name: {name}\n"
        f"Phone: {phone}\n"
        f"Service: {service}\n"
        f"Lead ID: {lead_id}\n"
        f"Priority: {lead.get('priority', 'N/A')}\n"
        f"AI Score: {lead.get('ai_score', 'N/A')}\n"
    )

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = ", ".join(notification_emails)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_user and smtp_pass:
                server.starttls()
                server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, notification_emails, msg.as_string())

        return "sent"
    except Exception:
        return "failed"


async def send_sms(lead: dict, funnel: dict) -> str:
    """
    Send SMS notification using Twilio.
    Returns status: "sent", "failed", "skipped_missing_config"
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = funnel.get("twilio_from_number") or ""

    answers = lead.get("answers_json", {})
    if isinstance(answers, str):
        answers = json.loads(answers)

    to_phone = answers.get("phone", "")

    if not account_sid or not auth_token or not from_number or not to_phone:
        return "skipped_missing_config"

    # Format phone if needed (add +1 if just digits)
    if to_phone.isdigit() and len(to_phone) == 10:
        to_phone = f"+1{to_phone}"
    elif not to_phone.startswith("+"):
        to_phone = f"+{to_phone}"

    name = answers.get("name", "a new lead")
    service = answers.get("service", "your service")
    message_body = f"New lead from {name} interested in {service}. Check your dashboard for details."

    try:
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data={
                    "From": from_number,
                    "To": to_phone,
                    "Body": message_body,
                },
            )
            resp.raise_for_status()
            return "sent"
    except Exception:
        return "failed"
