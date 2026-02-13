from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_pool, create_pool
from app.api.public import funnels as public_funnels
from app.api.public import leads as public_leads
from app.api.admin import auth as admin_auth
from app.api.admin import leads as admin_leads
from app.api.admin import funnels as admin_funnels
from app.api.admin import agency as admin_agency
from app.api.admin import dashboard as admin_dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(title="LeadForge API", lifespan=lifespan)

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

# Twilio webhook router (created by Agent B)
try:
    from app.api.public.twilio import router as public_twilio
    app.include_router(public_twilio, prefix="/public", tags=["Public Twilio"])
except ImportError:
    pass


@app.get("/health")
async def health():
    return {"status": "ok"}
