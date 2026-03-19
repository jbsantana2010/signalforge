"""
Notification service: sends email and SMS notifications for new leads
and handoff alerts when a lead requires human follow-up.
"""

import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import asyncpg

logger = logging.getLogger(__name__)

FALLBACK_FROM_EMAIL = "hello@warderai.com"


# ---------------------------------------------------------------------------
# Low-level send helpers
# ---------------------------------------------------------------------------

def send_email_notification(to_email: str, subject: str, body: str) -> str:
    """
    Send a plain-text email via SMTP.

    Reads config from env:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD (or SMTP_PASS), SMTP_FROM

    Returns "sent" | "skipped" | "failed".
    Never throws.
    """
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", "")

    if not smtp_host or not smtp_from:
        logger.warning(
            "send_email_notification: SMTP not configured (SMTP_HOST/SMTP_FROM missing) — skipping"
        )
        return "skipped"

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_user and smtp_pass:
                server.starttls()
                server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [to_email], msg.as_string())

        logger.info("send_email_notification: sent to %s", to_email)
        return "sent"
    except Exception as exc:
        logger.error("send_email_notification: failed to send to %s — %s", to_email, exc)
        return "failed"


def send_sms_notification(to_number: str, message: str) -> str:
    """
    Send an SMS via Twilio.

    Reads config from env:
      TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER

    Returns "sent" | "skipped" | "failed".
    Never throws.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_FROM_NUMBER", "")

    if not account_sid or not auth_token or not from_number:
        return "skipped"

    try:
        import httpx

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data={"From": from_number, "To": to_number, "Body": message},
            )
            resp.raise_for_status()

        logger.info("send_sms_notification: sent to %s", to_number)
        return "sent"
    except Exception as exc:
        logger.error("send_sms_notification: failed to send to %s — %s", to_number, exc)
        return "failed"


# ---------------------------------------------------------------------------
# Email content builder
# ---------------------------------------------------------------------------

def build_handoff_email(
    lead_name: str,
    lead_email: str,
    lead_phone: str,
    classification: str,
    message_body: str,
) -> tuple[str, str]:
    """
    Build (subject, body) for a handoff notification email.
    """
    display_name = lead_name or lead_email or "Unknown Lead"

    subject = f"New Lead Needs Attention — {display_name}"

    body = (
        f"A lead has replied and requires human follow-up.\n"
        f"\n"
        f"Lead Details\n"
        f"------------\n"
        f"Name:           {lead_name or 'N/A'}\n"
        f"Email:          {lead_email or 'N/A'}\n"
        f"Phone:          {lead_phone or 'N/A'}\n"
        f"\n"
        f"Their Message\n"
        f"-------------\n"
        f"{message_body or '(no message body)'}\n"
        f"\n"
        f"Classification: {classification or 'unknown'}\n"
        f"\n"
        f"Log in to Warder to follow up:\n"
        f"https://app.warderai.com\n"
    )

    return subject, body


# ---------------------------------------------------------------------------
# Rep contact lookup
# ---------------------------------------------------------------------------

async def get_rep_contact(
    conn: asyncpg.Connection,
    org_id: str,
    owner_email: str | None,
) -> dict | None:
    """
    Look up a rep contact by org_id + email.

    Returns {"email": ..., "phone": ..., "full_name": ...} or None.
    Never throws.
    """
    if not owner_email:
        return None
    try:
        row = await conn.fetchrow(
            """
            SELECT email, phone, full_name
            FROM rep_contacts
            WHERE org_id = $1 AND email = $2 AND is_active = true
            """,
            org_id,
            owner_email,
        )
        if row:
            return {"email": row["email"], "phone": row["phone"], "full_name": row["full_name"]}
    except Exception as exc:
        logger.warning("get_rep_contact: lookup failed for %s: %s", owner_email, exc)
    return None


# ---------------------------------------------------------------------------
# Handoff notification (core entry point)
# ---------------------------------------------------------------------------

async def notify_handoff_required(
    conn: asyncpg.Connection,
    lead_id: str,
    org_id: str,
    owner_email: str | None,
    reason: str,
    classification: str = "",
    message_body: str = "",
) -> None:
    """
    Notify the assigned rep (or fallback) that a lead needs human follow-up.

    1. Fetches lead info from DB.
    2. Looks up rep contact profile for rep phone number.
    3. Sends email notification to rep email (if SMTP configured).
    4. Sends SMS notification to rep phone from rep_contacts (if Twilio configured).
       Never sends to lead phone.
    5. Logs rep_notified engagement event with notification metadata.

    Never throws.
    """
    from app.services.engagement_service import log_engagement_event

    email_to: str | None = None
    email_status = "skipped"
    sms_to: str | None = None
    sms_status = "skipped"
    lead_name = ""
    lead_email_addr = ""
    lead_phone = ""

    try:
        # --- Fetch lead details ---
        lead_row = await conn.fetchrow(
            "SELECT answers_json FROM leads WHERE id = $1", lead_id
        )
        if lead_row:
            raw_answers = lead_row["answers_json"]
            if isinstance(raw_answers, str):
                answers = json.loads(raw_answers)
            elif raw_answers:
                answers = dict(raw_answers)
            else:
                answers = {}
            lead_name = answers.get("name", "")
            lead_phone = answers.get("phone", "")
            lead_email_addr = answers.get("email", "")

        # --- Resolve notification recipient ---
        email_to = owner_email or FALLBACK_FROM_EMAIL

        # --- Send email ---
        subject, body = build_handoff_email(
            lead_name=lead_name,
            lead_email=lead_email_addr,
            lead_phone=lead_phone,
            classification=classification,
            message_body=message_body,
        )
        email_status = send_email_notification(email_to, subject, body)

        # --- Send SMS to rep phone from rep_contacts (never to lead phone) ---
        rep_contact = await get_rep_contact(conn, org_id, owner_email)
        rep_phone = rep_contact["phone"] if rep_contact else None

        if rep_phone:
            sms_to = rep_phone
            sms_msg = "New lead needs attention. Check your Warder dashboard."
            sms_status = send_sms_notification(rep_phone, sms_msg)
        else:
            sms_status = "skipped_no_rep_phone"
            logger.info(
                "notify_handoff_required: no rep phone for %s — SMS skipped", owner_email
            )

    except Exception as exc:
        logger.error(
            "notify_handoff_required: unexpected error for lead %s: %s", lead_id, exc
        )

    # --- Log rep_notified event (always, even if sends failed) ---
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
                "classification": classification,
                "email": {"to": email_to, "status": email_status},
                "sms": {"to": sms_to, "status": sms_status},
            },
        )
        logger.info(
            "rep_notified event logged for lead %s — owner=%s email=%s sms=%s",
            lead_id, owner_email, email_status, sms_status,
        )
    except Exception as exc:
        logger.error(
            "notify_handoff_required: failed to log event for lead %s: %s", lead_id, exc
        )


# ---------------------------------------------------------------------------
# Lead acquisition notifications (existing — unchanged)
# ---------------------------------------------------------------------------

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
