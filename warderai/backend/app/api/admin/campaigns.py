"""Admin endpoints for campaign attribution."""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user, resolve_active_org_id
from app.database import get_db
from app.models.schemas import CreateCampaignRequest, UpdateCampaignRequest
from app.services.analytics_service import get_campaign_metrics

router = APIRouter()


@router.get("/campaigns")
async def list_campaigns(
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Return campaigns with attribution metrics for the active org."""
    return await get_campaign_metrics(conn, org_id)


@router.post("/campaigns", status_code=201)
async def create_campaign(
    body: CreateCampaignRequest,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Create a new campaign for the active org."""
    existing = await conn.fetchval(
        "SELECT id FROM campaigns WHERE org_id = $1 AND utm_campaign = $2",
        org_id,
        body.utm_campaign,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign with this utm_campaign already exists for this org",
        )

    row = await conn.fetchrow(
        """INSERT INTO campaigns (org_id, source, campaign_name, utm_campaign, ad_spend)
           VALUES ($1, $2, $3, $4, $5)
           RETURNING id, campaign_name, source, utm_campaign, ad_spend, created_at""",
        org_id,
        body.source,
        body.campaign_name,
        body.utm_campaign,
        body.ad_spend,
    )
    result = dict(row)
    result["id"] = str(result["id"])
    result["created_at"] = result["created_at"].isoformat()
    return result


@router.patch("/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: UUID,
    body: UpdateCampaignRequest,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Update ad_spend for a campaign."""
    result = await conn.execute(
        "UPDATE campaigns SET ad_spend = $1 WHERE id = $2 AND org_id = $3",
        body.ad_spend,
        campaign_id,
        org_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"ok": True}
