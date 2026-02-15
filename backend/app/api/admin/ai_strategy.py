"""Admin endpoint for AI-powered ad campaign strategy generation."""

import json

import asyncpg
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import resolve_active_org_id
from app.database import get_db
from app.services.ai_service import generate_ad_strategy

router = APIRouter()


class AdStrategyRequest(BaseModel):
    goal: str = "sales"  # sales | traffic | financing
    monthly_budget: float = 1000
    notes: str | None = None


@router.post("/ai/ad-strategy")
async def create_ad_strategy(
    body: AdStrategyRequest,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Generate a one-click AI ad campaign strategy for the active org."""

    # Load org data: industry, revenue settings, scoring config
    row = await conn.fetchrow(
        """
        SELECT o.avg_deal_value, o.close_rate_percent, o.scoring_config,
               i.slug AS industry_slug, i.name AS industry_name
        FROM orgs o
        LEFT JOIN industries i ON i.id = o.industry_id
        WHERE o.id = $1
        """,
        org_id,
    )

    org_data = {
        "industry_slug": row["industry_slug"] if row and row["industry_slug"] else "generic",
        "industry_name": row["industry_name"] if row and row["industry_name"] else "General Business",
        "avg_deal_value": float(row["avg_deal_value"] or 5000) if row else 5000,
        "close_rate_percent": float(row["close_rate_percent"] or 10) if row else 10,
        "scoring_config": None,
    }

    if row and row["scoring_config"]:
        sc = row["scoring_config"]
        org_data["scoring_config"] = json.loads(sc) if isinstance(sc, str) else sc

    result = await generate_ad_strategy(
        org_data=org_data,
        goal=body.goal,
        budget=body.monthly_budget,
        notes=body.notes,
    )

    return result
