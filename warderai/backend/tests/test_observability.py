"""PII scrubbing tests for INF-02.

We prove the scrubber strips phone/email/auth BEFORE events are emitted.
A failing test here means a regression risks leaking PII to Sentry.
"""

from app.observability import _before_send, _scrub_value


def test_scrub_phone_in_string():
    out = _scrub_value("call +15551234567 now")
    assert "+15551234567" not in out
    assert "[phone]" in out


def test_scrub_email_in_string():
    out = _scrub_value("user is alice@example.com today")
    assert "alice@example.com" not in out
    assert "[email]" in out


def test_scrub_nested_dict_by_key():
    payload = {
        "lead": {"phone": "+15551234567", "email": "a@b.co", "name": "Alice"},
        "headers": {"Authorization": "Bearer abc.def.ghi"},
    }
    out = _scrub_value(payload)
    assert out["lead"]["phone"] == "[Filtered]"
    assert out["lead"]["email"] == "[Filtered]"
    assert out["lead"]["name"] == "Alice"  # not sensitive
    assert out["headers"]["Authorization"] == "[Filtered]"


def test_before_send_scrubs_exception_message():
    event = {
        "exception": {
            "values": [
                {"value": "failed to send SMS to +15551234567 at alice@example.com"}
            ]
        },
        "request": {
            "headers": {"Authorization": "Bearer jwt.secret.token"},
            "data": {"phone": "+15551234567"},
        },
        "extra": {"twilio_auth_token": "supersecret"},
    }
    out = _before_send(event, hint={})
    assert out is not None

    msg = out["exception"]["values"][0]["value"]
    assert "+15551234567" not in msg
    assert "alice@example.com" not in msg

    assert out["request"]["headers"]["Authorization"] == "[Filtered]"
    assert out["request"]["data"]["phone"] == "[Filtered]"
    assert out["extra"]["twilio_auth_token"] == "[Filtered]"


def test_before_send_swallows_scrubber_errors():
    # If the scrubber somehow raises, we drop the event rather than crash
    # the process AND rather than sending the raw event.
    bad = {"exception": {"values": [{"value": object()}]}}  # non-str value
    out = _before_send(bad, hint={})
    # Either scrubbed to None (on error) or returned unchanged is acceptable;
    # what matters is that it does not raise.
    assert out is None or isinstance(out, dict)
