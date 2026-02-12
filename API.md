# LeadForge API Reference

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

## Public Endpoints (No Auth Required)

### GET /public/funnels/{slug}

Fetch funnel schema for rendering.

**Response 200:**
```json
{
  "slug": "solar-prime",
  "name": "Solar Prime Lead Funnel",
  "schema_json": {
    "slug": "solar-prime",
    "languages": ["en", "es"],
    "steps": [
      {
        "id": "service",
        "title": {"en": "What do you need?", "es": "¿Qué necesita?"},
        "fields": [...]
      }
    ]
  },
  "branding": {},
  "languages": ["en", "es"]
}
```

**Response 404:** Funnel not found

---

### POST /public/leads/submit

Submit a lead from a funnel.

**Request Body:**
```json
{
  "funnel_slug": "solar-prime",
  "answers": {
    "service": "solar",
    "zip_code": "90210",
    "name": "Jane Doe",
    "phone": "5551234567",
    "contact_time": "morning"
  },
  "language": "en",
  "source": {
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "solar-2024",
    "referrer": "https://google.com",
    "landing_url": "https://example.com/f/solar-prime?utm_source=google"
  },
  "honeypot": ""
}
```

**Response 200:**
```json
{
  "success": true,
  "message": "Lead submitted successfully"
}
```

**Validation Errors 422:** Missing required fields or invalid phone format.

**Spam Detection:** If `honeypot` field is non-empty, returns 200 with success=true (silent rejection, lead not stored).

---

## Admin Endpoints (JWT Required)

All admin endpoints require `Authorization: Bearer <token>` header.

### POST /admin/auth/login

**Request Body:**
```json
{
  "email": "admin@solarprime.com",
  "password": "admin123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### GET /admin/leads

List leads for the authenticated user's organization.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | int | 1 | Page number |
| per_page | int | 20 | Items per page |
| funnel_id | uuid | - | Filter by funnel |
| language | string | - | Filter by language (en/es) |
| search | string | - | Search name or phone |

**Response 200:**
```json
{
  "leads": [
    {
      "id": "uuid",
      "created_at": "2024-01-15T10:30:00Z",
      "name": "Jane Doe",
      "phone": "5551234567",
      "service": "solar",
      "language": "en",
      "score": null
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

---

### GET /admin/leads/{lead_id}

Get full lead details.

**Response 200:**
```json
{
  "id": "uuid",
  "org_id": "uuid",
  "funnel_id": "uuid",
  "language": "en",
  "answers_json": {
    "service": "solar",
    "zip_code": "90210",
    "name": "Jane Doe",
    "phone": "5551234567",
    "contact_time": "morning"
  },
  "source_json": {
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "solar-2024",
    "referrer": "https://google.com",
    "landing_url": "https://example.com/f/solar-prime"
  },
  "score": null,
  "is_spam": false,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### GET /admin/funnels

List funnels for the authenticated user's organization.

**Response 200:**
```json
{
  "funnels": [
    {
      "id": "uuid",
      "slug": "solar-prime",
      "name": "Solar Prime Lead Funnel",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### GET /admin/funnels/{funnel_id}

Get funnel details including automation settings.

**Response 200:**
```json
{
  "id": "uuid",
  "slug": "solar-prime",
  "name": "Solar Prime Lead Funnel",
  "is_active": true,
  "auto_email_enabled": false,
  "auto_sms_enabled": false,
  "auto_call_enabled": false,
  "notification_emails": [],
  "notification_phones": [],
  "rep_phone": null,
  "sms_template": "Hi {{name}}, thanks for your inquiry about {{service}}!",
  "working_hours_start": 9,
  "working_hours_end": 19,
  "routing_rules_json": [],
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### PATCH /admin/funnels/{funnel_id}

Update funnel automation settings.

**Request Body** (all fields optional):
```json
{
  "auto_email_enabled": true,
  "auto_sms_enabled": true,
  "auto_call_enabled": false,
  "notification_emails": ["alerts@solarprime.com"],
  "notification_phones": ["+15551234567"],
  "rep_phone": "+15559876543",
  "sms_template": "Hi {{name}}, thanks for your interest in {{service}}!",
  "working_hours_start": 8,
  "working_hours_end": 20,
  "routing_rules_json": [
    {
      "field": "service",
      "op": "eq",
      "value": "solar",
      "tags": ["solar"],
      "priority": "high"
    }
  ]
}
```

**Response 200:**
```json
{
  "id": "uuid",
  "slug": "solar-prime",
  "name": "Solar Prime Lead Funnel",
  "is_active": true,
  "auto_email_enabled": true,
  "auto_sms_enabled": true,
  "auto_call_enabled": false,
  "notification_emails": ["alerts@solarprime.com"],
  "notification_phones": ["+15551234567"],
  "rep_phone": "+15559876543",
  "sms_template": "Hi {{name}}, thanks for your interest in {{service}}!",
  "working_hours_start": 8,
  "working_hours_end": 20,
  "routing_rules_json": [
    {
      "field": "service",
      "op": "eq",
      "value": "solar",
      "tags": ["solar"],
      "priority": "high"
    }
  ],
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## Public Endpoints – Twilio Webhooks

These endpoints are called by Twilio. They are authenticated via a `secret` query parameter matching `TWILIO_WEBHOOK_SECRET`.

### POST /public/twilio/rep-answer?secret={secret}

Called when the rep answers a bridge call. Returns TwiML that announces the lead and gathers a keypress.

**Response 200 (application/xml):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather numDigits="1" action="/public/twilio/rep-gather?secret=...&amp;lead_id=...">
    <Say>New lead: Jane Doe, interested in solar. Press 1 to connect.</Say>
  </Gather>
  <Say>No input received. Goodbye.</Say>
</Response>
```

---

### POST /public/twilio/rep-gather?secret={secret}&lead_id={lead_id}

Called after the rep presses a digit. If "1", dials the lead. Otherwise, hangs up.

**Response 200 (application/xml) — Rep pressed 1:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Connecting you now.</Say>
  <Dial>+15551234567</Dial>
</Response>
```

**Response 200 (application/xml) — Rep pressed other:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Call declined. Goodbye.</Say>
</Response>
```

---

### POST /public/twilio/status?secret={secret}

Status callback for SMS and voice calls. Twilio posts status updates here.

**Form Parameters (from Twilio):**
| Param | Description |
|-------|-------------|
| MessageSid / CallSid | Twilio resource SID |
| MessageStatus / CallStatus | Current status (e.g. delivered, completed, failed) |

**Response 200:**
```json
{"status": "ok"}
```

---

## Updated Response Schemas (Sprint 2)

### GET /admin/leads – LeadListItem

```json
{
  "id": "uuid",
  "created_at": "2024-01-15T10:30:00Z",
  "name": "Jane Doe",
  "phone": "5551234567",
  "service": "solar",
  "language": "en",
  "score": 82,
  "tags": ["solar", "high-value"],
  "priority": "high"
}
```

New fields: `tags` (list of strings), `priority` (string or null).

---

### GET /admin/leads/{lead_id} – LeadDetail

```json
{
  "id": "uuid",
  "org_id": "uuid",
  "funnel_id": "uuid",
  "language": "en",
  "answers_json": {
    "service": "solar",
    "zip_code": "90210",
    "name": "Jane Doe",
    "phone": "5551234567",
    "contact_time": "morning"
  },
  "source_json": {
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "solar-2024",
    "referrer": "https://google.com",
    "landing_url": "https://example.com/f/solar-prime"
  },
  "score": 82,
  "score_summary": "High-intent solar lead in affluent zip code with morning availability.",
  "tags": ["solar", "high-value"],
  "priority": "high",
  "is_spam": false,
  "automation_log": [
    {"step": "routing", "status": "done", "ts": "2024-01-15T10:30:01Z"},
    {"step": "scoring", "status": "done", "ts": "2024-01-15T10:30:02Z"},
    {"step": "email", "status": "sent", "ts": "2024-01-15T10:30:03Z"},
    {"step": "sms", "status": "sent", "sid": "SM...", "ts": "2024-01-15T10:30:04Z"},
    {"step": "call", "status": "initiated", "sid": "CA...", "ts": "2024-01-15T10:30:05Z"}
  ],
  "created_at": "2024-01-15T10:30:00Z"
}
```

New fields: `score_summary` (string or null), `tags` (list of strings), `priority` (string or null), `automation_log` (list of log entries).
