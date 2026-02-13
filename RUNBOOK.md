# LeadForge – Sprint 1 Runbook

## Prerequisites

- Python 3.11+
- Node.js 18+ / npm
- PostgreSQL 14+ (running locally or via Docker)

## Quick Start with Docker (Postgres)

```bash
# Start Postgres (if not running)
docker run -d \
  --name leadforge-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=leadforge \
  -p 5432:5432 \
  postgres:16
```

## Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations and seed data
python seed.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

## Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at: http://localhost:3000

## Test the Application

1. **Public Funnel**: http://localhost:3000/f/solar-prime
   - Toggle between English and Spanish
   - Fill out the multi-step form
   - Submit to see the thank you page

2. **Admin Login**: http://localhost:3000/admin/login
   - Email: `admin@solarprime.com`
   - Password: `admin123`

3. **Admin Leads**: http://localhost:3000/admin/leads
   - View submitted leads
   - Click "View" to see lead details
   - Use search and language filter

## Environment Variables

### Backend (.env or environment)
| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql+asyncpg://postgres:postgres@localhost:5432/leadforge | Postgres connection string |
| JWT_SECRET | dev-secret-change-me | JWT signing secret |
| JWT_ALGORITHM | HS256 | JWT algorithm |
| JWT_EXPIRE_MINUTES | 480 | Token expiration |
| CORS_ORIGINS | http://localhost:3000 | Allowed CORS origins |

### Frontend (.env.local)
| Variable | Default | Description |
|----------|---------|-------------|
| NEXT_PUBLIC_API_URL | http://localhost:8000 | Backend API URL |

## Seed Data

The seed script creates:
- **Org**: SolarPrime Inc (slug: solarprime)
- **Admin User**: admin@solarprime.com / admin123
- **Funnel**: solar-prime (3-step solar/real estate lead funnel)
- **Sample Leads**: 5 leads with varied data

To re-seed (resets data):
```bash
cd backend
python seed.py
```

## Sprint 2: Automation Engine

### New Environment Variables

Add these to your `backend/.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLAUDE_API_KEY` | No | - | Anthropic API key for AI lead scoring. Falls back to deterministic stub if missing. |
| `SMTP_HOST` | No | - | SMTP server hostname for email notifications |
| `SMTP_PORT` | No | 587 | SMTP server port |
| `SMTP_USER` | No | - | SMTP authentication username |
| `SMTP_PASS` | No | - | SMTP authentication password |
| `SMTP_FROM` | No | - | From email address for notifications |
| `TWILIO_ACCOUNT_SID` | No | - | Twilio account SID for SMS and voice calls |
| `TWILIO_AUTH_TOKEN` | No | - | Twilio auth token |
| `TWILIO_WEBHOOK_SECRET` | No | `dev-webhook-secret` | Shared secret for validating Twilio webhook callbacks |
| `BASE_URL` | No | `http://localhost:8000` | Public base URL for webhook callbacks |

### Automation Features

Sprint 2 adds automatic lead processing on submission:
1. **Routing**: Tags and priority assignment based on funnel routing rules
2. **AI Scoring**: Lead score (0-100) and summary generation
3. **Email Notification**: Optional email to notification addresses
4. **SMS Notification**: Optional SMS to lead via Twilio
5. **Bridge Call**: Optional rep-to-lead phone bridge via Twilio Voice

All automation is non-blocking — lead submission returns immediately.

### Feature Toggles

Each funnel has independent toggles:
- `auto_email_enabled` — Send email notifications on new leads
- `auto_sms_enabled` — Send SMS to leads via Twilio
- `auto_call_enabled` — Initiate rep bridge calls via Twilio Voice

Configure via Admin UI: `/admin/funnels/{id}/settings`

### Working Hours

Bridge calls respect working hours (server time):
- `working_hours_start` (default: 9) — Hour to start placing calls (0-23)
- `working_hours_end` (default: 19) — Hour to stop placing calls (0-23)
- Outside this window, calls are skipped with status `skipped_outside_hours`

### Running Migration

The seed script automatically runs all migrations:
```bash
cd backend
python seed.py
```

### New Admin Endpoints

- `GET /admin/funnels/{id}` — Funnel detail with automation settings
- `PATCH /admin/funnels/{id}` — Update funnel automation settings

### New Public Endpoints (Twilio Webhooks)

- `POST /public/twilio/rep-answer` — TwiML for rep call answer
- `POST /public/twilio/rep-gather` — TwiML for rep digit input
- `POST /public/twilio/status` — Status callback for calls/SMS

## Sprint 4A: White-Label Foundation (Agency Layer)

### What Changed

- New `agencies` table with `id`, `name`, `created_at`
- `orgs` table now has an optional `agency_id` FK to `agencies`
- JWT tokens include `agency_id` claim when the user's org belongs to an agency
- Seed creates a default agency ("WaveLaunch Marketing") and links the demo org

### New Admin Endpoint

- `GET /admin/agency/orgs` — Lists all orgs for the current user's agency (falls back to single org if no agency)

### Migration

Run `python seed.py` to apply `004_agency.sql` and seed the default agency.

## Sprint 4B: Org Switcher + White-Label Branding

### What Changed

- New columns on `orgs`: `display_name`, `logo_url`, `primary_color`, `support_email` (migration `005_org_branding.sql`)
- `GET /admin/agency/orgs` now returns branding fields per org
- New `resolve_active_org_id` dependency in `auth.py` — reads `X-ORG-ID` header, validates against agency membership
- Admin endpoints (`/admin/leads`, `/admin/funnels`) use resolved org_id so agency users can view data for any org in their agency
- Frontend org switcher dropdown in admin nav (visible when agency has multiple orgs)
- All authenticated API calls inject `X-ORG-ID` header from `localStorage`
- Admin nav title and color adapt to the active org's branding

### How Org Switching Works

1. On login, frontend fetches `GET /admin/agency/orgs` to get available orgs
2. Active org ID is stored in `localStorage` (`leadforge_active_org_id`)
3. Every authenticated fetch includes `X-ORG-ID: <active_org_id>` header
4. Backend `resolve_active_org_id` validates the header org belongs to the user's agency
5. Non-agency users always see their home org (header is ignored)

### Migration

Run `python seed.py` to apply `005_org_branding.sql` and update seed data with branding fields.

## Sprint 4C: Agency Client Onboarding

### What Changed

- **POST /admin/agency/orgs** — Create a new client org under the current user's agency
- **POST /admin/agency/orgs/{org_id}/funnels** — Create a funnel for a target org with template defaults
- **Onboarding UI** at `/admin/agency/onboard` — Single-page form to create org + funnel in one flow
- "Onboard Client" nav link in admin layout (visible for agency users)
- After onboarding, the new org becomes the active org and user is redirected to funnels

### Onboarding Flow

1. Agency admin clicks "Onboard Client" in the admin nav
2. Fills in client org details (name, slug, branding) and funnel details (name, slug, sequence toggle)
3. On submit:
   - `POST /admin/agency/orgs` creates the org
   - `POST /admin/agency/orgs/{org_id}/funnels` creates a default 3-step funnel with routing rules and sequence config
   - Active org switches to the new org
   - Redirects to `/admin/funnels`
4. The org switcher dropdown now includes the new org

### Template Defaults (when schema_json omitted)

- **3-step form:** Service (solar/roofing/other) → Zip + Name → Phone + Contact Time
- **Routing rules:** service==solar → tag "solar", priority "high"
- **Sequence config (if enabled):** Day 0 welcome, Day 1 check-in, Day 3 follow-up

### New Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /admin/agency/orgs | JWT (agency) | Create client org |
| POST | /admin/agency/orgs/{org_id}/funnels | JWT (agency) | Create funnel for org |

## Sprint 4D: Revenue Intelligence Dashboard

### What Changed

- Migration `006_org_metrics.sql` adds `avg_deal_value` and `close_rate_percent` to `orgs`
- New `analytics_service.py` computes dashboard metrics from lead data
- `GET /admin/dashboard` returns KPIs (total leads, 7-day leads, AI distribution, response time, revenue estimate)
- `PATCH /admin/org/settings` updates deal value and close rate for the active org
- Dashboard page at `/admin/dashboard` with KPI cards and AI distribution bars
- Revenue Settings section added to funnel settings page
- "Dashboard" nav link added to admin layout

### Revenue Formula

```
estimated_revenue = total_leads × (close_rate_percent / 100) × avg_deal_value
```

### Migration

Run `python seed.py` to apply `006_org_metrics.sql` and seed default values (deal value: $5000, close rate: 10%).

### New Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /admin/dashboard | JWT + X-ORG-ID | Dashboard metrics |
| PATCH | /admin/org/settings | JWT + X-ORG-ID | Update deal value & close rate |
