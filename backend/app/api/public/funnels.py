import json

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.schemas import FunnelPublicResponse, FunnelSchema
from app.services.lead_service import get_funnel_by_slug

router = APIRouter()


@router.get("/funnels/{slug}", response_model=FunnelPublicResponse)
async def get_funnel(slug: str, conn: asyncpg.Connection = Depends(get_db)):
    row = await get_funnel_by_slug(conn, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Funnel not found")

    schema_raw = row["schema_json"]
    schema_data = json.loads(schema_raw) if isinstance(schema_raw, str) else schema_raw
    branding_raw = row["branding"]
    branding = json.loads(branding_raw) if isinstance(branding_raw, str) else (branding_raw or {})

    return FunnelPublicResponse(
        slug=row["slug"],
        name=row["name"],
        schema_json=FunnelSchema(**schema_data),
        branding=branding,
        languages=row["languages"],
    )
