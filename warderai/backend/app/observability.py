"""Sentry initialization and PII scrubbing (INF-02).

Pilot principle: Sentry is mandatory, but nothing sensitive leaves the
process. We strip leads' phone numbers, emails, message bodies, auth
tokens, and JWT claims before events are transmitted.

No-ops cleanly when SENTRY_DSN is unset so local dev runs untouched.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# Keys we never want leaving the process. Case-insensitive match on key name.
_SENSITIVE_KEYS = {
    "phone", "phone_number", "rep_phone", "rep_phone_number",
    "email", "email_address",
    "message", "message_body", "body", "sms_body",
    "password", "pass", "secret",
    "authorization", "auth", "token", "access_token", "refresh_token",
    "jwt", "cookie", "set-cookie",
    "twilio_auth_token", "anthropic_api_key", "claude_api_key",
    "smtp_pass", "smtp_password",
}

# E.164-ish phone pattern and RFC 5322-ish email pattern. Not perfect —
# just enough to catch casual leaks inside log messages and stack frames.
_PHONE_RE = re.compile(r"\+?\d[\d\-\s().]{7,}\d")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _scrub_value(value: Any) -> Any:
    """Recursively scrub a value. Dicts/lists get descended; strings get
    regex-scrubbed for phone/email patterns."""
    if isinstance(value, dict):
        return {k: ("[Filtered]" if k.lower() in _SENSITIVE_KEYS else _scrub_value(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    if isinstance(value, str):
        s = _PHONE_RE.sub("[phone]", value)
        s = _EMAIL_RE.sub("[email]", s)
        return s
    return value


def _before_send(event: dict, hint: dict) -> dict | None:
    """Sentry before_send hook. Scrubs request data, extra, breadcrumbs,
    and the exception message itself."""
    try:
        if "request" in event:
            req = event["request"]
            for k in ("headers", "cookies", "data", "query_string"):
                if k in req:
                    req[k] = _scrub_value(req[k])

        for k in ("extra", "contexts", "tags"):
            if k in event:
                event[k] = _scrub_value(event[k])

        # Scrub exception values (the message text, which frequently
        # includes formatted lead data).
        for ex in (event.get("exception") or {}).get("values", []) or []:
            if "value" in ex:
                ex["value"] = _scrub_value(ex["value"])

        for bc in event.get("breadcrumbs", {}).get("values", []) or []:
            if "data" in bc:
                bc["data"] = _scrub_value(bc["data"])
            if "message" in bc:
                bc["message"] = _scrub_value(bc["message"])
    except Exception:
        # Never let a scrubber crash kill an error report. Fail open-ish
        # (the raw event gets dropped on any exception here).
        logger.exception("Sentry scrubber failed; dropping event")
        return None

    return event


def init_sentry() -> bool:
    """Initialize Sentry if SENTRY_DSN is set. Returns True if active."""
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        logger.info("SENTRY_DSN not set; Sentry disabled")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning("sentry-sdk not installed; `pip install sentry-sdk`")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENV", "production"),
        release=os.getenv("WARDER_RELEASE") or None,
        send_default_pii=False,           # belt; scrubber is the suspenders
        traces_sample_rate=0.05,          # cheap tracing for pilot
        profiles_sample_rate=0.0,         # off for pilot
        before_send=_before_send,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            AsyncPGIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    logger.info("Sentry initialized (env=%s)", os.getenv("SENTRY_ENV", "production"))
    return True
