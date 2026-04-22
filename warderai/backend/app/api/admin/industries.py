"""Admin endpoints for industry profiles and templates."""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user
from app.database import get_db
from app.models.schemas import IndustryListItem, IndustryTemplateDetail

router = APIRouter()


@router.get("/admin/industries", response_model=list[IndustryListItem])
async def list_industries(
    _current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Return all available industries."""
    rows = await conn.fetch(
        "SELECT slug, name, description FROM industries ORDER BY name"
    )
    return [dict(r) for r in rows]


@router.get("/admin/industries/{slug}/template", response_model=IndustryTemplateDetail)
async def get_industry_template(
    slug: str,
    _current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Return the default template for an industry (for preview)."""
    row = await conn.fetchrow(
        """
        SELECT i.slug, i.name, i.description,
               t.default_funnel_json, t.default_sequence_json, t.default_scoring_json,
               t.default_avg_deal_value, t.default_close_rate_percent
        FROM industries i
        JOIN industry_templates t ON t.industry_id = i.id
        WHERE i.slug = $1
        """,
        slug,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Industry or template not found")
    return dict(row)
