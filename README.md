# SignalForge

**The 60-second lead response engine.** SignalForge captures leads, scores them with AI, and connects sales reps within seconds via automated calls, SMS, and email -- all from a single platform.

## Why SignalForge

Speed-to-lead is the #1 predictor of conversion. Studies show responding within 60 seconds increases close rates by 391%. Most CRMs take minutes to hours. SignalForge closes that gap with a fully automated response pipeline that fires the moment a lead submits a form.

## Features

| Feature | Description |
|---------|-------------|
| **Multi-step Lead Funnels** | Configurable, multi-language (EN/ES) form wizard with honeypot spam protection |
| **Intelligent Routing** | Rule-based tag and priority assignment from lead answers |
| **AI Lead Scoring** | Automatic 0-100 score + natural language summary (Claude API or deterministic fallback) |
| **Bridge Calls** | Twilio-powered rep-to-lead phone bridge -- rep answers, presses 1, instantly connected |
| **SMS Sequences** | Scheduled multi-step SMS follow-ups (immediate + timed drip) |
| **Missed-Call Text-Back** | Auto-sends SMS when a bridge call goes unanswered |
| **Email Notifications** | SMTP-based alerts to configurable notification addresses |
| **Working Hours** | Per-funnel call windows prevent off-hours outreach |
| **Multi-Tenancy** | Full org-level isolation -- every query scoped by `org_id` |
| **Feature Toggles** | Per-funnel on/off for email, SMS, calls, and sequences |

## Architecture

```
                         +-------------------+
                         |   Next.js 14 UI   |
                         |  (App Router, TS)  |
                         +--------+----------+
                                  |
                           REST / JWT Auth
                                  |
                         +--------v----------+
                         |    FastAPI         |
                         |  (async, Python)   |
                         +--------+----------+
                                  |
              +-------------------+-------------------+
              |                   |                   |
     +--------v------+  +--------v------+  +---------v--------+
     |  PostgreSQL    |  |  Twilio API   |  |  Claude API      |
     |  (asyncpg)     |  |  Voice + SMS  |  |  (AI scoring)    |
     +---------------+  +------+--------+  +------------------+
                               |
                    +----------+----------+
                    |  TwiML Webhooks     |
                    |  (rep-answer,       |
                    |   rep-gather,       |
                    |   status callback)  |
                    +--------------------+

Lead Submit Flow:
  Browser --> POST /public/leads/submit --> DB Insert --> Return 200
                                               |
                                    Background Task (non-blocking)
                                               |
                            +------------------v------------------+
                            |       process_automation()          |
                            |                                     |
                            |  1. Route  (tags + priority)        |
                            |  2. Score  (AI summary + score)     |
                            |  3. Email  (SMTP notification)      |
                            |  4. SMS    (Twilio message)         |
                            |  5. Call   (Twilio bridge)          |
                            |  6. Sequence (scheduled follow-ups) |
                            +-------------------------------------+
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Database | PostgreSQL 16, asyncpg (async connection pool) |
| Auth | JWT (HS256), bcrypt password hashing |
| Voice/SMS | Twilio Programmable Voice + Messaging |
| AI | Anthropic Claude API (optional, deterministic fallback) |
| Email | SMTP (any provider) |

## Local Setup

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
python seed.py          # runs migrations + seeds demo data
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Verify

- Public funnel: http://localhost:3000/f/solar-prime
- Admin login: http://localhost:3000/admin/login
  - `admin@solarprime.com` / `admin123`
- API docs: http://localhost:8000/docs

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://postgres:postgres@localhost:5432/leadforge` | Postgres connection |
| `JWT_SECRET` | Yes | `dev-secret-change-me` | JWT signing secret |
| `CORS_ORIGINS` | Yes | `http://localhost:3000` | Allowed CORS origins |
| `CLAUDE_API_KEY` | No | -- | Anthropic API key for AI scoring |
| `SMTP_HOST` | No | -- | SMTP server for email notifications |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | No | -- | SMTP username |
| `SMTP_PASS` | No | -- | SMTP password |
| `SMTP_FROM` | No | -- | Sender email address |
| `TWILIO_ACCOUNT_SID` | No | -- | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | No | -- | Twilio auth token |
| `TWILIO_WEBHOOK_SECRET` | No | `dev-webhook-secret` | Webhook validation secret |
| `BASE_URL` | No | `http://localhost:8000` | Public URL for Twilio callbacks |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Backend API URL |

> All Twilio/SMTP/Claude integrations gracefully degrade. Without credentials, features no-op with status `skipped_missing_config`.

## API Overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/public/funnels/{slug}` | No | Fetch funnel schema |
| `POST` | `/public/leads/submit` | No | Submit a lead |
| `POST` | `/public/twilio/rep-answer` | Secret | TwiML: rep call answer |
| `POST` | `/public/twilio/rep-gather` | Secret | TwiML: rep digit input |
| `POST` | `/public/twilio/status` | Secret | Twilio status callback |
| `POST` | `/admin/auth/login` | No | Admin login (returns JWT) |
| `GET` | `/admin/leads` | JWT | List leads (paginated, filterable) |
| `GET` | `/admin/leads/{id}` | JWT | Lead detail |
| `GET` | `/admin/leads/{id}/sequences` | JWT | Lead SMS sequence status |
| `GET` | `/admin/funnels` | JWT | List funnels |
| `GET` | `/admin/funnels/{id}` | JWT | Funnel detail + settings |
| `PATCH` | `/admin/funnels/{id}` | JWT | Update funnel settings |

Full docs: [`API.md`](API.md)

## Production Considerations

- **JWT_SECRET**: Generate a strong random secret (32+ chars). Never use the dev default.
- **Database**: Use a managed Postgres instance with connection pooling (PgBouncer).
- **HTTPS**: Terminate TLS at the load balancer. Twilio webhooks require HTTPS.
- **BASE_URL**: Must be a publicly reachable HTTPS URL for Twilio callbacks.
- **Task Queue**: Replace in-process `asyncio` background tasks with Celery + Redis for durable retries and horizontal scaling.
- **Rate Limiting**: Add API rate limiting on public endpoints (e.g., `slowapi`).
- **Webhook Validation**: Replace shared secret with Twilio request signature validation.
- **Monitoring**: Add structured logging, error tracking (Sentry), and uptime monitoring.
- **Multi-region**: Working hours currently use server time. Add per-funnel timezone support.
- **SMS Compliance**: Add opt-in/opt-out tracking and TCPA compliance before production SMS.

## Roadmap

| Sprint | Name | Status |
|--------|------|--------|
| 1 | Core Lead Capture MVP | Done |
| 2 | 60-Second Response Engine | Done |
| 3 | Visibility + Follow-Up Engine | Done |
| 4 | Real-Time Dashboard (WebSockets, live lead feed) | Planned |
| 5 | Funnel Builder UI (drag-and-drop form editor) | Planned |
| 6 | Analytics & Reporting (conversion funnels, rep performance) | Planned |
| 7 | Multi-channel (WhatsApp, Slack integrations) | Planned |
| 8 | Timezone + Compliance (per-funnel TZ, SMS opt-out) | Planned |

## License

Proprietary. All rights reserved.
