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

**Org Switching (Sprint 4B):** Agency users may pass `X-ORG-ID: <uuid>` header on any admin endpoint to operate on a different org within their agency. The backend validates that the target org belongs to the user's agency. Non-agency users or missing header defaults to the home org from the JWT.

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

### GET /admin/leads/{lead_id}/events

Automation event timeline for a lead, ordered chronologically.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Response 200:**
```json
{
  "events": [
    {
      "event_type": "routed",
      "status": "success",
      "detail_json": {"tags": ["solar"], "priority": "high"},
      "created_at": "2024-01-15T10:30:01Z"
    },
    {
      "event_type": "ai_scored",
      "status": "success",
      "detail_json": {"score": 80, "mode": "deterministic"},
      "created_at": "2024-01-15T10:30:02Z"
    },
    {
      "event_type": "email_sent",
      "status": "skipped_missing_config",
      "detail_json": null,
      "created_at": "2024-01-15T10:30:03Z"
    },
    {
      "event_type": "sequence_scheduled",
      "status": "success",
      "detail_json": null,
      "created_at": "2024-01-15T10:30:04Z"
    }
  ]
}
```

**Event types:** `routed`, `ai_scored`, `email_sent`, `sms_sent`, `call_started`, `sequence_scheduled`

**Statuses:** `success`, `sent`, `failed`, `skipped_missing_config`

```bash
curl http://localhost:8000/admin/leads/$LEAD_ID/events \
  -H "Authorization: Bearer $TOKEN"
```

---

## AI Strategy Endpoints (JWT Required)

### POST /admin/ai/ad-strategy

Generate a complete AI-powered ad campaign strategy for the active org. Uses org industry, deal value, close rate, and scoring config to produce tailored output. Falls back to deterministic stubs when Claude API key is not configured.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Request Body:**
```json
{
  "goal": "sales",
  "monthly_budget": 2000,
  "notes": "Focus on first-time buyers"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| goal | No | "sales" | Campaign goal: sales, traffic, or financing |
| monthly_budget | No | 1000 | Monthly ad budget in dollars |
| notes | No | null | Optional context for the AI |

**Response 200:**
```json
{
  "angles": [
    "Dream boat lifestyle — freedom on the water",
    "Trade-in upgrade path — your current boat is worth more than you think"
  ],
  "hooks": [
    "Your dream boat is closer than you think.",
    "What if your next weekend looked like this?"
  ],
  "offers": [
    "Free trade-in appraisal — no obligation",
    "Pre-approval in minutes with 0% down options"
  ],
  "targeting": [
    "Homeowners 30-65 within 50mi of waterways",
    "Fishing and boating enthusiast audiences"
  ],
  "ads": [
    {
      "primary_text": "Your weekends deserve an upgrade. Browse our curated selection...",
      "headline": "Find Your Perfect Boat Today",
      "cta": "Browse Inventory"
    }
  ],
  "mode": "claude"
}
```

The `mode` field indicates whether the response was generated by Claude (`"claude"`) or by the deterministic fallback (`"stub"`).

```bash
curl -X POST http://localhost:8000/admin/ai/ad-strategy \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"goal":"sales","monthly_budget":2000}'
```

---

## Campaign Endpoints (JWT Required)

All campaign endpoints use `resolve_active_org_id` — they respect the `X-ORG-ID` header for agency org switching.

### GET /admin/campaigns

List campaigns with attribution metrics for the active org. Sorted by creation date descending.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Response 200:**
```json
{
  "campaigns": [
    {
      "id": "uuid",
      "campaign_name": "Summer Solar Push",
      "source": "google",
      "utm_campaign": "solar-summer",
      "leads": 3,
      "avg_ai_score": 76.7,
      "estimated_revenue": 1500.0,
      "ad_spend": 250.0,
      "cost_per_lead": 83.33,
      "roas": 6.0
    }
  ]
}
```

Derived fields:
- `estimated_revenue` = leads x (close_rate_percent / 100) x avg_deal_value
- `cost_per_lead` = ad_spend / leads (null if leads == 0)
- `roas` = estimated_revenue / ad_spend (null if ad_spend == 0)

```bash
curl http://localhost:8000/admin/campaigns \
  -H "Authorization: Bearer $TOKEN"
```

---

### POST /admin/campaigns

Create a new campaign for the active org.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Request Body:**
```json
{
  "campaign_name": "Summer Solar Push",
  "source": "google",
  "utm_campaign": "solar-summer",
  "ad_spend": 250.00
}
```

| Field | Required | Description |
|-------|----------|-------------|
| campaign_name | Yes | Human-readable campaign name |
| source | Yes | Platform: facebook, google, tiktok, manual |
| utm_campaign | Yes | UTM campaign key (matched against lead source_json) |
| ad_spend | No | Total ad spend in dollars (default: 0) |

**Response 201:**
```json
{
  "id": "uuid",
  "campaign_name": "Summer Solar Push",
  "source": "google",
  "utm_campaign": "solar-summer",
  "ad_spend": 250.0,
  "created_at": "2024-01-15T10:00:00Z"
}
```

**409:** Campaign with this utm_campaign already exists for this org.

```bash
curl -X POST http://localhost:8000/admin/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"campaign_name":"Summer Solar Push","source":"google","utm_campaign":"solar-summer","ad_spend":250}'
```

---

### PATCH /admin/campaigns/{campaign_id}

Update the ad spend for a campaign.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Request Body:**
```json
{
  "ad_spend": 500.00
}
```

**Response 200:**
```json
{"ok": true}
```

**404:** Campaign not found or doesn't belong to this org.

```bash
curl -X PATCH http://localhost:8000/admin/campaigns/$CAMPAIGN_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ad_spend": 500}'
```

---

## Industry Endpoints (JWT Required)

### GET /admin/industries

List all available industry profiles.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
[
  {"slug": "generic", "name": "Generic", "description": "Default industry profile for general-purpose lead capture"},
  {"slug": "marine_dealer", "name": "Marine Dealer", "description": "Boat dealerships and marine sales organizations"},
  {"slug": "equipment_dealer", "name": "Equipment Dealer", "description": "Heavy equipment and machinery dealerships"}
]
```

```bash
curl http://localhost:8000/admin/industries \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /admin/industries/{slug}/template

Preview the default template for an industry, including funnel schema, sequence config, scoring rubric, and revenue defaults.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "slug": "marine_dealer",
  "name": "Marine Dealer",
  "description": "Boat dealerships and marine sales organizations",
  "default_funnel_json": {"languages": ["en"], "steps": [...]},
  "default_sequence_json": {"steps": [...]},
  "default_scoring_json": {"rubric": "Score marine leads 0-100..."},
  "default_avg_deal_value": 12000,
  "default_close_rate_percent": 12
}
```

**404:** Industry or template not found.

```bash
curl http://localhost:8000/admin/industries/marine_dealer/template \
  -H "Authorization: Bearer $TOKEN"
```

---

## Agency Endpoints (JWT Required, Sprint 4A)

### GET /admin/agency/orgs

List all orgs belonging to the current user's agency. If the user has no agency, returns only their own org.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "orgs": [
    {
      "id": "uuid",
      "name": "SolarPrime Inc",
      "slug": "solarprime",
      "display_name": "SolarPrime",
      "logo_url": null,
      "primary_color": "#f59e0b",
      "support_email": "support@solarprime.com",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

### POST /admin/agency/orgs

Create a new client org under the current user's agency.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Acme Solar",
  "slug": "acme-solar",
  "display_name": "Acme Solar Co",
  "primary_color": "#10b981",
  "support_email": "support@acmesolar.com",
  "logo_url": "https://example.com/logo.png",
  "industry_slug": "marine_dealer"
}
```

The optional `industry_slug` field selects an industry profile. When provided, the org is pre-configured with the industry's default avg deal value, close rate, and scoring config. The funnel created via `/admin/agency/orgs/{org_id}/funnels` will use the industry's template schema and sequence config. If omitted or invalid, falls back to `generic`.

**Response 201:**
```json
{
  "id": "uuid",
  "name": "Acme Solar",
  "slug": "acme-solar",
  "display_name": "Acme Solar Co",
  "logo_url": "https://example.com/logo.png",
  "primary_color": "#10b981",
  "support_email": "support@acmesolar.com"
}
```

**403:** User has no agency_id.
**409:** Slug already in use.

```bash
# Example curl
curl -X POST http://localhost:8000/admin/agency/orgs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Solar","slug":"acme-solar","display_name":"Acme","industry_slug":"marine_dealer"}'
```

---

### POST /admin/agency/orgs/{org_id}/funnels

Create a funnel for a target org (agency admin only). If `schema_json` is omitted, a 3-step template (Service, Contact, Phone) is used with default routing rules and sequence config.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Main Lead Funnel",
  "slug": "main-funnel",
  "enable_sequences": true,
  "enable_email": false,
  "enable_sms": false,
  "enable_call": false
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "slug": "main-funnel",
  "org_id": "uuid"
}
```

**403:** User has no agency_id or org doesn't belong to their agency.
**409:** Funnel slug already exists for this org.

```bash
# Example curl
curl -X POST http://localhost:8000/admin/agency/orgs/$ORG_ID/funnels \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Main Funnel","slug":"main-funnel","enable_sequences":true}'
```

---

### GET /admin/dashboard

Revenue intelligence dashboard metrics for the active org.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Response 200:**
```json
{
  "metrics": {
    "total_leads": 5,
    "leads_last_7_days": 2,
    "avg_response_seconds": 3600.0,
    "contacted_percent": 20.0,
    "ai_hot_count": 1,
    "ai_warm_count": 2,
    "ai_cold_count": 1,
    "call_connect_rate": 0,
    "estimated_revenue": 2500.0,
    "avg_deal_value": 5000,
    "close_rate_percent": 10
  }
}
```

```bash
curl http://localhost:8000/admin/dashboard \
  -H "Authorization: Bearer $TOKEN"
```

---

### PATCH /admin/org/settings

Update revenue metrics (avg deal value, close rate) for the active org.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Request Body (all fields optional):**
```json
{
  "avg_deal_value": 7500,
  "close_rate_percent": 15
}
```

**Response 200:**
```json
{"ok": true}
```

```bash
curl -X PATCH http://localhost:8000/admin/org/settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"avg_deal_value": 7500, "close_rate_percent": 15}'
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
