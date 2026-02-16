from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user, resolve_active_org_id
from app.database import get_db
from app.models.schemas import LeadDetail, LeadListItem, LeadListResponse, LeadStageUpdateRequest
from app.services.lead_service import get_lead_detail, get_leads

VALID_STAGES = {"new", "contacted", "qualified", "appointment", "won", "lost"}

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


@router.patch("/leads/{lead_id}/stage")
async def update_lead_stage(
    lead_id: UUID,
    body: LeadStageUpdateRequest,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    if body.stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {', '.join(sorted(VALID_STAGES))}")

    if body.stage == "won" and not body.deal_amount:
        raise HTTPException(status_code=400, detail="deal_amount is required when stage is 'won'")

    deal_amount = body.deal_amount if body.stage == "won" else None

    result = await conn.fetchrow(
        """
        UPDATE leads
        SET stage = $1, deal_amount = $2, stage_updated_at = NOW()
        WHERE id = $3 AND org_id = $4
        RETURNING id, org_id, funnel_id, language, answers_json, source_json,
                  score, is_spam, created_at,
                  tags, priority, ai_summary, ai_score,
                  email_status, sms_status, call_status, call_attempts,
                  contact_status, last_contacted_at,
                  stage, deal_amount, stage_updated_at
        """,
        body.stage,
        deal_amount,
        str(lead_id),
        org_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")

    import json
    answers = json.loads(result["answers_json"]) if isinstance(result["answers_json"], str) else result["answers_json"]
    source = json.loads(result["source_json"]) if isinstance(result["source_json"], str) else result["source_json"]

    return LeadDetail(
        id=result["id"],
        org_id=result["org_id"],
        funnel_id=result["funnel_id"],
        language=result["language"],
        answers_json=answers,
        source_json=source,
        score=float(result["score"]) if result["score"] is not None else None,
        is_spam=result["is_spam"],
        created_at=result["created_at"],
        tags=list(result["tags"]) if result["tags"] else None,
        priority=result["priority"],
        ai_summary=result["ai_summary"],
        ai_score=result["ai_score"],
        email_status=result["email_status"],
        sms_status=result["sms_status"],
        call_status=result["call_status"],
        call_attempts=result["call_attempts"] or 0,
        contact_status=result["contact_status"],
        last_contacted_at=result["last_contacted_at"],
        stage=result["stage"] or "new",
        deal_amount=float(result["deal_amount"]) if result["deal_amount"] is not None else None,
        stage_updated_at=result["stage_updated_at"],
    )


@router.post("/leads/{lead_id}/assist")
async def lead_conversion_assist(
    lead_id: UUID,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Generate AI conversion assist (next action, scripts) for a lead."""
    import json as _json

    # Load lead
    lead_row = await conn.fetchrow(
        """SELECT id, answers_json, stage, ai_score, ai_summary
           FROM leads WHERE id = $1 AND org_id = $2""",
        str(lead_id), org_id,
    )
    if not lead_row:
        raise HTTPException(status_code=404, detail="Lead not found")

    answers = _json.loads(lead_row["answers_json"]) if isinstance(lead_row["answers_json"], str) else lead_row["answers_json"]

    # Load org context
    org_row = await conn.fetchrow(
        """SELECT o.avg_deal_value, o.close_rate_percent, o.scoring_config,
                  i.name AS industry_name
           FROM orgs o
           LEFT JOIN industries i ON i.id = o.industry_id
           WHERE o.id = $1""",
        org_id,
    )

    org_data = {
        "industry_name": org_row["industry_name"] if org_row and org_row["industry_name"] else "general business",
        "avg_deal_value": float(org_row["avg_deal_value"] or 5000) if org_row else 5000,
        "close_rate_percent": float(org_row["close_rate_percent"] or 10) if org_row else 10,
        "scoring_config": (
            _json.loads(org_row["scoring_config"])
            if org_row and org_row["scoring_config"] and isinstance(org_row["scoring_config"], str)
            else (org_row["scoring_config"] if org_row else None)
        ),
    }

    lead_data = {
        "name": answers.get("name", "there"),
        "stage": lead_row["stage"] or "new",
        "answers": answers,
        "ai_score": lead_row["ai_score"],
        "ai_summary": lead_row["ai_summary"],
        "service": answers.get("service", ""),
    }

    from app.services.ai_service import generate_conversion_assist
    result = await generate_conversion_assist(org_data, lead_data)
    return result


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
