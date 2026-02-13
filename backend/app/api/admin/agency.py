"""Admin agency endpoints."""
import json
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user, resolve_active_org_id
from app.database import get_db
from app.models.schemas import (
    CreateFunnelRequest,
    CreateFunnelResponse,
    CreateOrgRequest,
    CreateOrgResponse,
    OrgMetricsUpdateRequest,
)

router = APIRouter()

_ORG_COLS = "id, name, slug, display_name, logo_url, primary_color, support_email, created_at"

# Default 3-step funnel template used when schema_json is omitted
_DEFAULT_SCHEMA = {
    "languages": ["en"],
    "steps": [
        {
            "id": "service",
            "title": {"en": "What service do you need?"},
            "fields": [
                {
                    "key": "service",
                    "type": "select",
                    "required": True,
                    "label": {"en": "Service"},
                    "options": [
                        {"value": "solar", "label": {"en": "Solar Installation"}},
                        {"value": "roofing", "label": {"en": "Roofing"}},
                        {"value": "other", "label": {"en": "Other"}},
                    ],
                }
            ],
        },
        {
            "id": "contact_info",
            "title": {"en": "Your Information"},
            "fields": [
                {"key": "zip_code", "type": "text", "required": True, "label": {"en": "Zip Code"}},
                {"key": "name", "type": "text", "required": True, "label": {"en": "Full Name"}},
            ],
        },
        {
            "id": "phone_info",
            "title": {"en": "Contact Preferences"},
            "fields": [
                {"key": "phone", "type": "tel", "required": True, "label": {"en": "Phone Number"}},
                {"key": "contact_time", "type": "select", "required": False, "label": {"en": "Best time to call"}, "options": [
                    {"value": "morning", "label": {"en": "Morning"}},
                    {"value": "afternoon", "label": {"en": "Afternoon"}},
                    {"value": "evening", "label": {"en": "Evening"}},
                ]},
            ],
        },
    ],
}

_DEFAULT_ROUTING = {
    "rules": [
        {"when": {"field": "service", "equals": "solar"}, "then": {"tag": "solar", "priority": "high"}},
    ]
}

_DEFAULT_SEQUENCE = {
    "steps": [
        {"delay_minutes": 0, "message": "Thanks for your request, {{name}}! We'll be in touch shortly."},
        {"delay_minutes": 1440, "message": "Hi {{name}}, just checking in on your inquiry. Any questions?"},
        {"delay_minutes": 4320, "message": "Hi {{name}}, we'd love to help — reply to schedule a call!"},
    ]
}


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


# ── Sprint 4C: Create Org under Agency ──────────────────────────────────


@router.post("/agency/orgs", response_model=CreateOrgResponse, status_code=201)
async def create_agency_org(
    body: CreateOrgRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Create a new client org under the current user's agency."""
    agency_id = current_user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agency membership required")

    # Check slug uniqueness
    existing = await conn.fetchval("SELECT id FROM orgs WHERE slug = $1", body.slug)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    row = await conn.fetchrow(
        """INSERT INTO orgs (name, slug, agency_id, display_name, logo_url, primary_color, support_email)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           RETURNING id, name, slug, display_name, logo_url, primary_color, support_email""",
        body.name,
        body.slug,
        agency_id,
        body.display_name,
        body.logo_url,
        body.primary_color,
        body.support_email,
    )
    return dict(row)


# ── Sprint 4C: Create Funnel for Target Org ─────────────────────────────


@router.post("/agency/orgs/{org_id}/funnels", response_model=CreateFunnelResponse, status_code=201)
async def create_org_funnel(
    org_id: UUID,
    body: CreateFunnelRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Create a funnel for a target org (agency admin only)."""
    agency_id = current_user.get("agency_id")
    if not agency_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agency membership required")

    # Validate org belongs to this agency
    target = await conn.fetchval(
        "SELECT id FROM orgs WHERE id = $1 AND agency_id = $2", org_id, agency_id
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Org not accessible")

    # Check funnel slug uniqueness within org
    existing = await conn.fetchval(
        "SELECT id FROM funnels WHERE slug = $1 AND org_id = $2", body.slug, org_id
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Funnel slug already exists for this org")

    schema = body.schema_json if body.schema_json else {**_DEFAULT_SCHEMA, "slug": body.slug}
    routing = json.dumps(_DEFAULT_ROUTING)
    seq_config = json.dumps(_DEFAULT_SEQUENCE) if body.enable_sequences else None
    languages = schema.get("languages", [body.language_default])

    row = await conn.fetchrow(
        """INSERT INTO funnels
               (org_id, slug, name, schema_json, languages, is_active,
                routing_rules, sequence_enabled, sequence_config,
                auto_email_enabled, auto_sms_enabled, auto_call_enabled)
           VALUES ($1, $2, $3, $4, $5, true, $6, $7, $8, $9, $10, $11)
           RETURNING id, slug, org_id""",
        org_id,
        body.slug,
        body.name,
        json.dumps(schema),
        languages,
        routing,
        body.enable_sequences,
        seq_config,
        body.enable_email,
        body.enable_sms,
        body.enable_call,
    )
    return dict(row)


# ── Sprint 4D: Update Org Metrics ───────────────────────────────────────


@router.patch("/org/settings")
async def update_org_settings(
    body: OrgMetricsUpdateRequest,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Update revenue metrics for the active org."""
    set_parts = []
    params = []
    idx = 1

    for field in ("avg_deal_value", "close_rate_percent"):
        val = getattr(body, field, None)
        if val is not None:
            set_parts.append(f"{field} = ${idx}")
            params.append(float(val))
            idx += 1

    if not set_parts:
        return {"ok": True}

    params.append(org_id)
    await conn.execute(
        f"UPDATE orgs SET {', '.join(set_parts)} WHERE id = ${idx}",
        *params,
    )
    return {"ok": True}
