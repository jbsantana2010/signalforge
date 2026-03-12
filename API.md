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

### POST /public/leads/basin

Receive Basin form webhook submissions from warderai.com. Creates a lead directly in the Warder org under the `website-demo` funnel. No auth required. No signature validation (future work).

**Request Body (Basin webhook JSON):**
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "5551234567",
  "company": "Acme Corp",
  "website": "https://acme.com",
  "message": "I'd like a product demo",
  "lang": "en",
  "page": "https://warderai.com/demo",
  "referrer": "https://google.com",
  "timestamp": "2026-03-06T12:00:00Z"
}
```

All fields are optional. Unknown fields are ignored. Only `name` and `email` together are used for deduplicate detection.

**Response 200 (created):**
```json
{
  "status": "ok",
  "lead_id": "uuid-of-new-lead",
  "org_slug": "warder",
  "funnel_slug": "website-demo"
}
```

**Response 200 (duplicate suppressed):**
```json
{
  "status": "duplicate_ignored"
}
```
Returned when the same `name` + `email` pair arrives within 5 minutes. No lead is created.

**Response 404:** Org `warder` or funnel `website-demo` not found (run `python seed.py` to create them).

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

### PATCH /admin/leads/{lead_id}/stage

Update the pipeline stage of a lead. When stage is `won`, `deal_amount` is required.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Request Body:**
```json
{
  "stage": "won",
  "deal_amount": 8400.00
}
```

| Field | Required | Description |
|-------|----------|-------------|
| stage | Yes | One of: `new`, `contacted`, `qualified`, `appointment`, `won`, `lost` |
| deal_amount | Conditional | Required when stage is `won`. Ignored for other stages. |

**Response 200:** Returns full `LeadDetail` with updated stage, deal_amount, and stage_updated_at.

**400:** Invalid stage or missing deal_amount when stage is `won`.

**404:** Lead not found or doesn't belong to this org.

```bash
curl -X PATCH http://localhost:8000/admin/leads/$LEAD_ID/stage \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stage":"won","deal_amount":8400}'
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

## AI Conversion Assist (JWT Required)

### POST /admin/leads/{lead_id}/assist

Generate AI-powered conversion coaching for a specific lead. Returns a next best action, SMS/email scripts, and call talking points tailored to the lead's pipeline stage and form answers. Falls back to deterministic stage-based scripts when Claude API key is not configured.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Request Body:** None (POST with empty body)

**Response 200:**
```json
{
  "mode": "claude",
  "data": {
    "next_action": "Make immediate contact within 5 minutes. Speed to lead is critical.",
    "sms_script": "Hi John, thanks for reaching out about solar! When's a good time for a quick call?",
    "email_script": "Hi John,\n\nThank you for your inquiry about solar installation...",
    "call_talking_points": [
      "Introduce yourself and reference their solar interest",
      "Ask about their timeline and roof condition",
      "Identify budget range and financing preferences",
      "Offer a free site assessment"
    ]
  }
}
```

The `mode` field indicates `"claude"` (AI-generated) or `"stub"` (deterministic fallback). Scripts are personalized with the lead's name and adapt to their current pipeline stage.

**404:** Lead not found or doesn't belong to this org.

```bash
curl -X POST http://localhost:8000/admin/leads/$LEAD_ID/assist \
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

---

## Engagement Engine V1

### GET /admin/leads/{id}/engagement

Returns the active engagement plan, scheduled steps, and engagement events for a lead.

**Auth:** JWT + X-ORG-ID

**Response 200:**
```json
{
  "plan": {
    "id": "uuid",
    "lead_id": "uuid",
    "org_id": "uuid",
    "funnel_id": "uuid",
    "status": "active",
    "current_step": 1,
    "paused": false,
    "escalation_reason": null,
    "created_at": "...",
    "updated_at": "..."
  },
  "steps": [
    {
      "id": "uuid",
      "plan_id": "uuid",
      "step_order": 1,
      "channel": "sms",
      "action_type": "send",
      "scheduled_for": "...",
      "executed_at": "...",
      "status": "sent",
      "template_key": "intro_sms_1",
      "generated_content_json": { "sms_body": "Hi ..." },
      "created_at": "..."
    }
  ],
  "events": [
    {
      "id": "uuid",
      "lead_id": "uuid",
      "org_id": "uuid",
      "channel": "sms",
      "event_type": "sms_sent",
      "direction": "outbound",
      "content": "Hi John, thanks for...",
      "metadata_json": { "step_id": "uuid", "status": "sent" },
      "created_at": "..."
    }
  ]
}
```

**Step statuses:** `pending` | `sent` | `skipped_missing_config` | `failed`

**Default V1 step schedule (from plan creation):**
- Step 1 — SMS  — now + 30 seconds
- Step 2 — Email — now + 2 minutes
- Step 3 — SMS  — now + 1 hour
- Step 4 — Email — now + 24 hours

**Current limitations (V1):**
- No inbound SMS reply handling yet
- No AI-generated content (deterministic templates only)
- Call channel steps are skipped with `skipped_missing_config`
- No escalation logic yet

---

## Engagement Engine V1.1 (Scheduler + Reliability)

### POST /admin/ops/engagement/run

Manually trigger processing of all due engagement steps for the active org.
Admin-only. Not public.

**Headers:** `Authorization: Bearer <token>`, `X-ORG-ID: <uuid>` (optional)

**Request Body:** None

**Response 200:**
```json
{
  "status": "ok",
  "processed": 3,
  "sent": 2,
  "skipped_missing_config": 1,
  "failed": 0
}
```

- `processed` — total steps evaluated this run
- `sent` — successfully delivered
- `skipped_missing_config` — delivery skipped (missing Twilio/SMTP config, or call channel)
- `failed` — delivery attempted and failed

```bash
curl -X POST http://localhost:8000/admin/ops/engagement/run \
  -H "Authorization: Bearer $TOKEN"
```

---

### Engagement Event Metadata (V1.1)

All events logged by the worker now include enriched metadata:

```json
{
  "step_id": "uuid",
  "step_order": 1,
  "plan_id": "uuid",
  "status": "sent"
}
```

### Call Channel Behavior (V1.1)

Call channel steps are always skipped with `skipped_missing_config`.
The worker logs `call_not_supported_v1` as the reason. No crash occurs.

### Engagement Empty State

`GET /admin/leads/{id}/engagement` always returns a valid response even when no plan exists:

```json
{
  "plan": null,
  "steps": [],
  "events": []
}
```

Never returns 500 for missing data.

The response now also includes `inbound_messages`:

```json
{
  "plan": {...},
  "steps": [...],
  "events": [...],
  "inbound_messages": [
    {
      "id": "uuid",
      "lead_id": "uuid",
      "org_id": "uuid",
      "channel": "sms",
      "message_body": "This is too expensive",
      "classification": "price",
      "suggested_response": "I understand...",
      "metadata_json": {"from_number": "+15551234567"},
      "created_at": "2026-03-11T..."
    }
  ]
}
```

---

## Inbound Reply Intelligence (V2)

### POST /public/inbound/sms

Receive an inbound SMS reply from a lead.

**No authentication required** (public endpoint — Twilio webhook compatible).

**Request Body:**

```json
{
  "from": "+15551234567",
  "body": "This is too expensive"
}
```

Also accepts Twilio PascalCase fields (`From`, `Body`) and snake_case (`from_number`, `body`).

**Response:**

```json
{
  "status": "ok",
  "classification": "price",
  "suggested_response": "I understand. Many customers feel the same at first..."
}
```

**Behavior:**

1. Identifies lead by phone number (fuzzy 10-digit suffix match)
2. Creates `inbound_messages` row with classification + suggested_response
3. Creates `engagement_event` with `event_type: sms_reply`, `direction: inbound`
4. If `classification` is `human_needed` or `unknown`: pauses the engagement plan and creates `escalated_to_human` event
5. Returns classification and suggested response — does NOT auto-send any reply

**Classifications:**

| Value | Trigger Keywords |
|-------|-----------------|
| `interested` | yes, interested, tell me more, sure, sign me up |
| `price` | price, expensive, cost, too much, afford |
| `timing` | later, not ready, maybe next month, wait |
| `info` | info, information, how does, question, explain |
| `not_interested` | no thanks, stop, not interested, unsubscribe |
| `human_needed` | help, human, agent, real person, speak to |
| `unknown` | (fallback — no keyword match) |

**Escalation:**

When classification is `human_needed` or `unknown`:
- `engagement_plans.paused` is set to `true`
- `engagement_plans.escalation_reason` = `reply_requires_human`
- An `escalated_to_human` engagement event is created
- The outbound worker will skip paused plans automatically
