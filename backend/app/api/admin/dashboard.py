"""Admin dashboard endpoint."""

import asyncpg
from fastapi import APIRouter, Depends

from app.core.auth import resolve_active_org_id
from app.database import get_db
from app.services.analytics_service import get_org_dashboard_metrics

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    metrics = await get_org_dashboard_metrics(conn, org_id)
    return {"metrics": metrics}
