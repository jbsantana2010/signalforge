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
