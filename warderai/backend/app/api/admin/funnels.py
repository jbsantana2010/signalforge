from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user, resolve_active_org_id
from app.database import get_db
from app.models.schemas import FunnelDetail, FunnelListItem, FunnelUpdateRequest
from app.services.lead_service import get_funnel_detail, get_funnels_for_org, update_funnel_settings

router = APIRouter()


@router.get("/funnels", response_model=list[FunnelListItem])
async def list_funnels(
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    funnels = await get_funnels_for_org(conn, org_id)
    return [FunnelListItem(**f) for f in funnels]


@router.get("/funnels/{funnel_id}", response_model=FunnelDetail)
async def get_funnel(
    funnel_id: UUID,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    detail = await get_funnel_detail(conn, org_id, str(funnel_id))
    if not detail:
        raise HTTPException(status_code=404, detail="Funnel not found")
    return FunnelDetail(**detail)


@router.patch("/funnels/{funnel_id}", response_model=FunnelDetail)
async def update_funnel(
    funnel_id: UUID,
    payload: FunnelUpdateRequest,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    result = await update_funnel_settings(conn, org_id, str(funnel_id), updates)
    if not result:
        raise HTTPException(status_code=404, detail="Funnel not found")
    return FunnelDetail(**result)
