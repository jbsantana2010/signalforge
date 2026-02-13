from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user, resolve_active_org_id
from app.database import get_db
from app.models.schemas import LeadDetail, LeadListItem, LeadListResponse
from app.services.lead_service import get_lead_detail, get_leads

router = APIRouter()


@router.get("/leads", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    funnel_id: UUID | None = Query(None),
    language: str | None = Query(None),
    search: str | None = Query(None),
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    funnel_id_str = str(funnel_id) if funnel_id else None

    items, total = await get_leads(
        conn=conn,
        org_id=org_id,
        page=page,
        per_page=per_page,
        funnel_id=funnel_id_str,
        language=language,
        search=search,
    )

    return LeadListResponse(
        leads=[LeadListItem(**item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/leads/{lead_id}", response_model=LeadDetail)
async def get_lead(
    lead_id: UUID,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    detail = await get_lead_detail(conn, org_id, str(lead_id))
    if not detail:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadDetail(**detail)


@router.get("/leads/{lead_id}/sequences")
async def get_sequences(
    lead_id: UUID,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    # Verify lead belongs to org
    lead = await conn.fetchval(
        "SELECT id FROM leads WHERE id = $1 AND org_id = $2",
        str(lead_id), org_id,
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    from app.services.lead_service import get_lead_sequences
    sequences = await get_lead_sequences(conn, str(lead_id))
    return sequences


@router.get("/leads/{lead_id}/events")
async def get_lead_events(
    lead_id: UUID,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Return automation events for a lead, ordered chronologically."""
    # Verify lead belongs to org
    lead = await conn.fetchval(
        "SELECT id FROM leads WHERE id = $1 AND org_id = $2",
        str(lead_id), org_id,
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    import json
    rows = await conn.fetch(
        """SELECT event_type, status, detail_json, created_at
           FROM automation_events
           WHERE lead_id = $1 AND org_id = $2
           ORDER BY created_at ASC""",
        str(lead_id), org_id,
    )
    events = []
    for r in rows:
        detail = r["detail_json"]
        if isinstance(detail, str):
            detail = json.loads(detail)
        events.append({
            "event_type": r["event_type"],
            "status": r["status"],
            "detail_json": detail,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return {"events": events}
