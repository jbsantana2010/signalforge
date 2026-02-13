# SignalForge

**White-Label Revenue Acceleration Platform**

AI-powered lead response and follow-up system built for agencies and high-ticket businesses. Captures leads, scores them with AI, and connects sales teams within 60 seconds via automated calls, SMS, and email.

## Core Capabilities

| Capability | Description |
|------------|-------------|
| **60-Second Response Engine** | Automated call bridge, SMS, and email fire the moment a lead submits |
| **AI Lead Scoring** | Claude-powered 0-100 scoring with natural language summaries (deterministic fallback) |
| **SMS Sequences** | Multi-step scheduled follow-ups (Day 0, Day 1, Day 3 drip campaigns) |
| **Call Bridge** | Twilio-powered rep-to-lead phone connection with working hours enforcement |
| **Multi-Org White Label** | Agency manages multiple client orgs with isolated data, branding, and funnels |
| **Revenue Intelligence** | Dashboard with KPIs, AI lead distribution, and estimated revenue projections |
| **Client Onboarding** | One-click org + funnel provisioning from agency admin UI |
| **Intelligent Routing** | Rule-based tag and priority assignment from lead answers |
| **Ops Readiness** | Health endpoint and status page for deployment verification |

## Architecture

```
Agency
 └── Org (white-label branding, revenue settings)
      └── Funnel (form schema, routing rules, automation config)
           └── Lead (answers, AI score, contact status, sequences)
```

```
 Next.js 14 (App Router)                FastAPI (async)
 ┌──────────────────────┐               ┌──────────────────────┐
 │  Dashboard           │    REST/JWT   │  Admin API           │
 │  Lead Management     │◄────────────►│  Public API          │
 │  Funnel Settings     │               │  Automation Engine   │
 │  Onboarding          │               │  Analytics Service   │
 │  Ops Status          │               │  Health Check        │
 └──────────────────────┘               └──────┬───────────────┘
                                               │
                            ┌──────────────────┼──────────────────┐
                            │                  │                  │
                       PostgreSQL         Twilio API         Claude API
                       (asyncpg)         (Voice + SMS)      (AI scoring)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Database | PostgreSQL 16, asyncpg |
| Auth | JWT (HS256), bcrypt |
| Voice/SMS | Twilio Programmable Voice + Messaging |
| AI | Anthropic Claude API (optional) |
| Email | SMTP (any provider) |

## Multi-Tenant Model

```
Agency (WaveLaunch Marketing)
 ├── Org: SolarPrime Inc     → Funnel: solar-prime     → Leads (isolated)
 ├── Org: Acme Roofing       → Funnel: acme-leads      → Leads (isolated)
 └── Org: ...
```

- Each org has its own branding (logo, color, display name)
- JWT contains `agency_id` — enables org switching via `X-ORG-ID` header
- All queries scoped by `org_id` — zero data leakage between orgs

## Revenue Model

```
Estimated Revenue = Total Leads x (Close Rate % / 100) x Avg Deal Value
```

Configurable per org via funnel settings. Displayed on the revenue intelligence dashboard.

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16+ (or Docker)

### 1. Database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python seed.py          # migrations + demo data
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Verify

- Health check: http://localhost:8000/health
- Public funnel: http://localhost:3000/f/solar-prime
- Admin login: http://localhost:3000/admin/login (`admin@solarprime.com` / `admin123`)
- Dashboard: http://localhost:3000/admin/dashboard
- Ops status: http://localhost:3000/admin/ops
- API docs: http://localhost:8000/docs

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` | Postgres connection |
| `JWT_SECRET` | Yes | `dev-secret-change-me` | JWT signing secret |
| `CORS_ORIGINS` | Yes | `http://localhost:3000` | Allowed origins |
| `CLAUDE_API_KEY` | No | — | AI lead scoring |
| `SMTP_HOST` | No | — | Email notifications |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | No | — | SMTP username |
| `SMTP_PASS` | No | — | SMTP password |
| `SMTP_FROM` | No | — | Sender address |
| `TWILIO_ACCOUNT_SID` | No | — | SMS + voice |
| `TWILIO_AUTH_TOKEN` | No | — | Twilio auth |
| `TWILIO_WEBHOOK_SECRET` | No | `dev-webhook-secret` | Webhook validation |
| `BASE_URL` | No | `http://localhost:8000` | Public URL for callbacks |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Backend API URL |

All external integrations (Twilio, SMTP, Claude) gracefully degrade when not configured.

## API Overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | No | System readiness with service status |
| `GET` | `/public/funnels/{slug}` | No | Fetch funnel schema |
| `POST` | `/public/leads/submit` | No | Submit a lead |
| `POST` | `/admin/auth/login` | No | Admin login |
| `GET` | `/admin/dashboard` | JWT | Revenue intelligence metrics |
| `GET` | `/admin/leads` | JWT | List leads (paginated) |
| `GET` | `/admin/leads/{id}` | JWT | Lead detail |
| `GET` | `/admin/funnels` | JWT | List funnels |
| `GET`/`PATCH` | `/admin/funnels/{id}` | JWT | Funnel detail / settings |
| `GET` | `/admin/agency/orgs` | JWT | List agency orgs |
| `POST` | `/admin/agency/orgs` | JWT | Create client org |
| `POST` | `/admin/agency/orgs/{id}/funnels` | JWT | Create funnel for org |
| `PATCH` | `/admin/org/settings` | JWT | Update revenue settings |

Full reference: [`API.md`](API.md) | Pilot ops: [`RUNBOOK_PILOT.md`](RUNBOOK_PILOT.md)

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| Core Platform | Lead capture, AI scoring, automation engine | Done |
| White Label | Agency layer, org switcher, branding, onboarding | Done |
| Revenue Intelligence | Dashboard, KPIs, estimated revenue | Done |
| Pilot Ops | Health checks, status page, deployment runbook | Done |
| Stripe Billing | Per-org subscription management | Planned |
| AI Voice Agent | Conversational AI for inbound/outbound calls | Planned |
| Advanced Analytics | Conversion funnels, rep performance, cohort analysis | Planned |
| Event Timeline | Per-lead activity feed with full automation history | Planned |

## License

Proprietary. All rights reserved.
