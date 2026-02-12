import asyncpg
from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.database import get_db
from app.models.schemas import FunnelListItem
from app.services.lead_service import get_funnels_for_org

router = APIRouter()


@router.get("/funnels", response_model=list[FunnelListItem])
async def list_funnels(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    org_id = current_user["org_id"]
    funnels = await get_funnels_for_org(conn, org_id)
    return [FunnelListItem(**f) for f in funnels]
