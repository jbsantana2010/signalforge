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
