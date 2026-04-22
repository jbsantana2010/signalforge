# SignalForge Pilot Deployment Runbook

## Required Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Postgres connection string |
| `JWT_SECRET` | Yes | Strong random secret (32+ chars). **Never use dev default.** |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins (e.g. `https://app.yourdomain.com`) |
| `TWILIO_ACCOUNT_SID` | For SMS/calls | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | For SMS/calls | Twilio auth token |
| `TWILIO_WEBHOOK_SECRET` | For calls | Webhook validation secret |
| `BASE_URL` | For calls | Publicly reachable HTTPS URL for Twilio callbacks |
| `SMTP_HOST` | For email | SMTP server hostname |
| `SMTP_PORT` | For email | SMTP port (default: 587) |
| `SMTP_USER` | For email | SMTP username |
| `SMTP_PASS` | For email | SMTP password |
| `SMTP_FROM` | For email | Sender email address |
| `CLAUDE_API_KEY` | For AI scoring | Anthropic API key (falls back to deterministic scoring) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (e.g. `https://api.yourdomain.com`) |

## Deployment Steps

### 1. Database (Docker)

```bash
docker run -d \
  --name signalforge-db \
  -e POSTGRES_USER=signalforge \
  -e POSTGRES_PASSWORD=<STRONG_PASSWORD> \
  -e POSTGRES_DB=signalforge \
  -p 5432:5432 \
  -v signalforge_pgdata:/var/lib/postgresql/data \
  postgres:16
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure .env with production values
cp .env.example .env  # edit with real credentials

# Run migrations + seed
python seed.py

# Start (production)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 3. Frontend

```bash
cd frontend
npm install
npm run build
npm start  # or deploy to Vercel/Netlify
```

## Health Verification

```bash
# Check system readiness
curl http://localhost:8000/health | python -m json.tool

# Expected output:
# {
#   "status": "ok",
#   "database": "connected",
#   "twilio_configured": true,
#   "smtp_configured": true,
#   "claude_configured": true
# }
```

If `status` is `error`, check database connectivity first.

Services showing `false` will degrade gracefully (no crashes), but those features won't work.

## Funnel Test Checklist

1. Open public funnel URL: `https://<domain>/f/<funnel-slug>`
2. Verify all form steps render correctly
3. Submit a test lead with valid phone number
4. Confirm lead appears in admin dashboard within 5 seconds
5. If Twilio configured: verify SMS received on test phone
6. If SMTP configured: verify email notification arrives
7. If AI enabled: confirm `ai_score` and `ai_summary` populated on lead detail
8. Switch orgs via org switcher — verify data isolation
9. Check `/admin/ops` — all expected services show green

## Daily Monitoring Checklist

- [ ] `GET /health` returns `"status": "ok"`
- [ ] Database connection pool healthy (no timeout errors in logs)
- [ ] Check `/admin/ops` page for service status
- [ ] Review `/admin/dashboard` for lead volume trends
- [ ] Confirm new leads from the past 24h are being scored
- [ ] If SMS enabled: spot-check a recent lead's `sms_status` (should be `sent`)
- [ ] Monitor server logs for `WARNING` or `ERROR` entries
- [ ] Check disk usage on Postgres data volume

## Rollback Instructions

### Application Rollback

```bash
# Stop current process
pkill -f "uvicorn app.main:app"

# Checkout previous version
git log --oneline -5        # find target commit
git checkout <commit-hash>

# Re-deploy
cd backend && pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### Database Rollback

Migrations are additive (ALTER TABLE ADD COLUMN IF NOT EXISTS). Rolling back application code is safe without reversing migrations — new columns are simply unused by older code.

If a migration must be reversed:

```bash
# Connect to DB
psql -U signalforge -d signalforge

# Manually drop added columns (example)
ALTER TABLE orgs DROP COLUMN IF EXISTS avg_deal_value;
ALTER TABLE orgs DROP COLUMN IF EXISTS close_rate_percent;
```

### Frontend Rollback

```bash
cd frontend
git checkout <commit-hash>
npm install && npm run build && npm start
```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `/health` returns `"database": "error"` | Verify `DATABASE_URL`, check Postgres is running |
| Leads not scoring | Check `CLAUDE_API_KEY` in env; review logs for AI service errors |
| SMS not sending | Verify `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN`; check Twilio dashboard |
| Emails not sending | Verify `SMTP_HOST` + `SMTP_USER`; test SMTP connectivity |
| CORS errors in browser | Verify `CORS_ORIGINS` includes frontend URL |
| JWT errors | Check `JWT_SECRET` matches between restarts |
