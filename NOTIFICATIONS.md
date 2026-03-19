# Notifications Setup

Warder sends real-time notifications when a lead requires human follow-up
(classification: `human_needed` or `unknown`).

Notifications are **optional** — if config is missing, the system logs the
`rep_notified` event and continues without crashing.

---

## Email Notifications (SMTP)

Set these environment variables to enable email alerts:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-address@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-address@gmail.com
```

### Gmail example

1. Enable 2FA on the Google account.
2. Generate an App Password (Google Account → Security → App Passwords).
3. Use the app password as `SMTP_PASSWORD`.

### Behavior

| Config state          | Result                                |
|-----------------------|---------------------------------------|
| SMTP fully configured | Email sent to `owner_email` (or org admin, or `hello@warderai.com`) |
| `SMTP_HOST` missing   | Skipped — warning logged              |
| Send fails            | Error logged, event still recorded    |

---

## SMS Notifications (Twilio)

Set these environment variables to enable SMS alerts:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+15550001234
```

`TWILIO_FROM_NUMBER` must be a Twilio-provisioned number in E.164 format.

SMS is sent to the **rep's phone number** stored in `rep_contacts`, not to the
lead's phone. If no rep contact exists or the rep has no phone configured,
the SMS is skipped with status `skipped_no_rep_phone`.

### Behavior

| Config / rep state                     | Result                              |
|----------------------------------------|-------------------------------------|
| Twilio configured + rep has phone      | SMS sent to rep phone               |
| Twilio configured + rep has no phone   | `skipped_no_rep_phone`              |
| Twilio configured + no rep contact     | `skipped_no_rep_phone`              |
| Any Twilio variable missing            | `skipped` (silently)                |
| Send fails                             | Error logged, flow continues        |

---

## Rep Contact Profiles

Rep contacts live in the `rep_contacts` table (migration `017_rep_contacts.sql`)
and are managed via the **Rep Contacts** admin page or API.

### API

```
GET  /admin/rep-contacts          — list all contacts for current org
POST /admin/rep-contacts          — create or upsert by email
PATCH /admin/rep-contacts/{id}    — update phone / full_name / is_active
```

### Fields

| Field       | Type    | Notes                                 |
|-------------|---------|---------------------------------------|
| `email`     | TEXT    | Must match `leads.owner_email`        |
| `phone`     | TEXT    | E.164 format, e.g. `+17875550100`     |
| `full_name` | TEXT    | Display name only                     |
| `is_active` | BOOLEAN | Inactive contacts are excluded        |

Seeded rep for SolarPrime: `rep@solarprime.com` / `+17875550100` / "Solar Rep"

---

## Notification routing

### Email recipient priority

1. `leads.owner_email` (assigned rep)
2. First admin user in the org (`users` table, `ORDER BY created_at ASC`)
3. `hello@warderai.com` (global fallback)

### SMS recipient

1. `rep_contacts` row matching `(org_id, owner_email)` — uses `phone` field
2. No rep contact or no phone → `skipped_no_rep_phone`

---

## Event logging

Every handoff attempt logs a `rep_notified` event in `engagement_events`
regardless of whether sends succeed. The event metadata includes:

```json
{
  "owner_email": "rep@solarprime.com",
  "reason": "reply_requires_human",
  "classification": "human_needed",
  "email": { "to": "rep@solarprime.com", "status": "sent" },
  "sms":   { "to": "+17875550100",       "status": "sent" }
}
```

Possible `status` values:

| Status                | Meaning                                              |
|-----------------------|------------------------------------------------------|
| `sent`                | Sent successfully                                    |
| `skipped`             | Config missing (SMTP_HOST or Twilio vars absent)     |
| `skipped_no_rep_phone`| Twilio ready but rep has no phone in rep_contacts    |
| `failed`              | Config present but send threw an error               |

---

## Testing locally

### Without SMTP/Twilio (default dev setup)

No config needed — notifications skip gracefully. Trigger a handoff by sending
an inbound SMS from Maria Garcia's seeded phone number:

```bash
# Snake-case format
curl -X POST http://127.0.0.1:8000/public/inbound/sms \
  -H "Content-Type: application/json" \
  -d '{"from_number": "+17865559876", "body": "I need to speak with someone"}'

# Twilio PascalCase format (same endpoint accepts both)
curl -X POST http://127.0.0.1:8000/public/inbound/sms \
  -H "Content-Type: application/json" \
  -d '{"From": "+17865559876", "Body": "I need to speak with someone"}'
```

> **Note:** The endpoint identifies leads by phone number, not lead ID.
> Maria Garcia's seeded phone is `7865559876` (stored without country code).
> The endpoint normalises to last 10 digits for matching, so `+17865559876` works.

Check that a `rep_notified` event was logged:

```bash
psql $DATABASE_URL -c "
  SELECT metadata_json FROM engagement_events
  WHERE event_type = 'rep_notified'
  ORDER BY created_at DESC LIMIT 3;
"
```

You should see `sms.status = "skipped_no_rep_phone"` if Twilio is not configured,
or `sms.status = "skipped"` if the rep contact exists but Twilio vars are missing.

### With SMTP (Mailhog for local testing)

```bash
# Run Mailhog
docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Set env vars
export SMTP_HOST=localhost
export SMTP_PORT=1025
export SMTP_FROM=warder@local.dev
# SMTP_USER and SMTP_PASSWORD not needed for Mailhog
```

Trigger a handoff with the curl above → open http://localhost:8025 to see the email.

### With Twilio configured

Ensure the seeded rep contact has a real phone:

```bash
# Via API (after login)
curl -X POST http://127.0.0.1:8000/admin/rep-contacts \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-ORG-ID: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{"email": "rep@solarprime.com", "phone": "+1REAL_NUMBER", "full_name": "Solar Rep"}'
```

Then trigger a handoff via the inbound SMS curl above.
The rep at `+1REAL_NUMBER` should receive an SMS.

---

## Known limitations (V4.1)

- `send_sms_notification` uses synchronous `httpx.Client` (acceptable since
  notifications are fire-and-forget)
- No retry logic — failed sends are logged but not retried
- No delivery confirmation beyond HTTP 2xx from Twilio
- Rep phone must be in the `rep_contacts` table; per-funnel `rep_phone_number`
  is a separate field used only for lead acquisition, not handoff alerts
