"""Admin agency endpoints."""
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.database import get_db

router = APIRouter()

_ORG_COLS = "id, name, slug, display_name, logo_url, primary_color, support_email, created_at"


@router.get("/agency/orgs")
async def list_agency_orgs(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """List orgs for the current user's agency. Falls back to user's own org."""
    agency_id = current_user.get("agency_id")

    if agency_id:
        rows = await conn.fetch(
            f"SELECT {_ORG_COLS} FROM orgs WHERE agency_id = $1 ORDER BY created_at",
            agency_id,
        )
    else:
        rows = await conn.fetch(
            f"SELECT {_ORG_COLS} FROM orgs WHERE id = $1",
            current_user["org_id"],
        )

    return {
        "orgs": [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "slug": row["slug"],
                "display_name": row["display_name"],
                "logo_url": row["logo_url"],
                "primary_color": row["primary_color"],
                "support_email": row["support_email"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
    }
