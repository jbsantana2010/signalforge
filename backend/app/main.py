import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_pool, create_pool, pool as _pool_ref
import app.database as _db_mod

logger = logging.getLogger("signalforge")

from app.api.public import funnels as public_funnels
from app.api.public import leads as public_leads
from app.api.admin import auth as admin_auth
from app.api.admin import leads as admin_leads
from app.api.admin import funnels as admin_funnels
from app.api.admin import agency as admin_agency
from app.api.admin import dashboard as admin_dashboard
from app.api.admin import industries as admin_industries
from app.api.admin import campaigns as admin_campaigns
from app.api.admin import ai_strategy as admin_ai_strategy
from app.api.admin import ops as admin_ops
from app.api.admin import rep_contacts as admin_rep_contacts


def _service_flags() -> dict:
    return {
        "twilio": bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN),
        "smtp": bool(settings.SMTP_HOST and settings.SMTP_USER),
        "claude": bool(settings.CLAUDE_API_KEY),
    }


def _log_env_summary(db_ok: bool):
    flags = _service_flags()
    lines = [
        "",
        "  SignalForge Environment Status",
        "  ──────────────────────────────",
        f"  Database:   {'OK' if db_ok else 'ERROR'}",
        f"  Twilio:     {'ENABLED' if flags['twilio'] else 'DISABLED'}",
        f"  SMTP:       {'ENABLED' if flags['smtp'] else 'DISABLED'}",
        f"  Claude AI:  {'ENABLED' if flags['claude'] else 'DISABLED'}",
        "",
    ]
    logger.info("\n".join(lines))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    # Verify DB connectivity and log environment
    db_ok = False
    try:
        async with _db_mod.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception as exc:
        logger.error(f"Database connectivity check failed: {exc}")
    _log_env_summary(db_ok)

    # Start persistent engagement scheduler (runs every 60 seconds)
    async def _run_engagement_worker():
        try:
            from app.services.engagement_worker import process_due_engagement_steps
            result = await process_due_engagement_steps(_db_mod.pool)
            if result.get("processed", 0) > 0:
                logger.info("Engagement worker: %s", result)
        except Exception as exc:
            logger.error("Engagement scheduler error: %s", exc)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_run_engagement_worker, "interval", seconds=60, id="engagement_worker")
    scheduler.start()
    logger.info("Engagement scheduler started (interval: 60s)")

    yield

    scheduler.shutdown(wait=False)
    await close_pool()


app = FastAPI(title="SignalForge API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_funnels.router, prefix="/public", tags=["Public Funnels"])
app.include_router(public_leads.router, prefix="/public", tags=["Public Leads"])
app.include_router(admin_auth.router, prefix="/admin", tags=["Admin Auth"])
app.include_router(admin_leads.router, prefix="/admin", tags=["Admin Leads"])
app.include_router(admin_funnels.router, prefix="/admin", tags=["Admin Funnels"])
app.include_router(admin_agency.router, prefix="/admin", tags=["Admin Agency"])
app.include_router(admin_dashboard.router, prefix="/admin", tags=["Admin Dashboard"])
app.include_router(admin_industries.router, tags=["Admin Industries"])
app.include_router(admin_campaigns.router, prefix="/admin", tags=["Admin Campaigns"])
app.include_router(admin_ai_strategy.router, prefix="/admin", tags=["Admin AI Strategy"])
app.include_router(admin_ops.router, prefix="/admin", tags=["Admin Ops"])
app.include_router(admin_rep_contacts.router, prefix="/admin", tags=["Admin Rep Contacts"])

# Twilio webhook router (created by Agent B)
try:
    from app.api.public.twilio import router as public_twilio
    app.include_router(public_twilio, prefix="/public", tags=["Public Twilio"])
except ImportError:
    pass

# Inbound SMS reply handler
from app.api.public.inbound_sms import router as public_inbound_sms
app.include_router(public_inbound_sms, prefix="/public", tags=["Public Inbound"])


@app.get("/health")
async def health():
    """Enhanced readiness check with service status."""
    db_status = "connected"
    try:
        async with _db_mod.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        db_status = "error"

    flags = _service_flags()
    status = "ok" if db_status == "connected" else "error"

    return {
        "status": status,
        "database": db_status,
        "twilio_configured": flags["twilio"],
        "smtp_configured": flags["smtp"],
        "claude_configured": flags["claude"],
    }
