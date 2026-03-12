from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user, resolve_active_org_id
from app.database import get_db
from app.models.schemas import LeadDetail, LeadEngagementResponse, LeadIntelligenceResponse, LeadListItem, LeadListResponse, LeadStageUpdateRequest, LeadStageUpdateResponse, StageHistoryItem, EngagementPlanItem, EngagementStepItem, EngagementEventItem, InboundMessageItem
from app.services.lead_service import get_lead_detail, get_leads, get_stage_history, insert_stage_history, update_pipeline_fields
from app.services.lead_intelligence_service import compute_lead_intelligence, intelligence_to_dict

VALID_STAGES = {"new", "contacted", "qualified", "proposal", "won", "lost"}

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
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    if body.stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {', '.join(sorted(VALID_STAGES))}")

    if body.stage == "won" and not body.deal_amount:
        raise HTTPException(status_code=400, detail="deal_amount is required when stage is 'won'")

    # Outcome reason required for won/lost
    if body.stage in ("won", "lost") and not body.outcome_reason:
        raise HTTPException(status_code=400, detail="outcome_reason is required when closing a deal (won/lost)")

    # Get current stage before update
    current_stage = await conn.fetchval(
        "SELECT stage FROM leads WHERE id = $1 AND org_id = $2",
        str(lead_id), org_id,
    )
    if current_stage is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    deal_amount = body.deal_amount if body.deal_amount is not None else None

    # Set closed_at when transitioning to won/lost
    from datetime import datetime, timezone
    closed_at = None
    if body.stage in ("won", "lost") and (current_stage or "new") not in ("won", "lost"):
        closed_at = datetime.now(timezone.utc)

    updated = await update_pipeline_fields(
        conn=conn,
        org_id=org_id,
        lead_id=str(lead_id),
        stage=body.stage,
        deal_amount=deal_amount,
        next_action_at=body.next_action_at,
        next_action_note=body.next_action_note,
        outcome_reason=body.outcome_reason if body.stage in ("won", "lost") else None,
        outcome_note=body.outcome_note if body.stage in ("won", "lost") else None,
        closed_at=closed_at,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Insert history only if stage actually changed
    history_event_id = None
    if (current_stage or "new") != body.stage:
        history_event_id = await insert_stage_history(
            conn=conn,
            org_id=org_id,
            lead_id=str(lead_id),
            from_stage=current_stage or "new",
            to_stage=body.stage,
            changed_by_user_id=current_user.get("user_id"),
            reason=body.reason,
        )

    # Compute intelligence and merge into lead
    intel = compute_lead_intelligence(
        stage=updated["stage"],
        ai_score=updated.get("ai_score"),
        deal_amount=updated.get("deal_amount"),
        stage_updated_at=updated.get("stage_updated_at"),
        last_contacted_at=updated.get("last_contacted_at"),
        created_at=updated.get("created_at"),
    )
    updated.update(intelligence_to_dict(intel))

    return LeadStageUpdateResponse(
        lead=LeadDetail(**updated),
        history_event_id=history_event_id,
    )


@router.get("/leads/{lead_id}/stage-history")
async def get_lead_stage_history(
    lead_id: UUID,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Return recent stage history for a lead."""
    lead = await conn.fetchval(
        "SELECT id FROM leads WHERE id = $1 AND org_id = $2",
        str(lead_id), org_id,
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    history = await get_stage_history(conn, org_id, str(lead_id))
    return {"history": [StageHistoryItem(**h) for h in history]}


@router.get("/leads/{lead_id}/intelligence", response_model=LeadIntelligenceResponse)
async def get_lead_intelligence(
    lead_id: UUID,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Compute live intelligence signals for a lead."""
    row = await conn.fetchrow(
        """SELECT stage, ai_score, deal_amount, stage_updated_at,
                  last_contacted_at, created_at
           FROM leads WHERE id = $1 AND org_id = $2""",
        str(lead_id), org_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")

    intel = compute_lead_intelligence(
        stage=row["stage"] or "new",
        ai_score=row["ai_score"],
        deal_amount=float(row["deal_amount"]) if row["deal_amount"] is not None else None,
        stage_updated_at=row["stage_updated_at"],
        last_contacted_at=row["last_contacted_at"],
        created_at=row["created_at"],
    )
    return LeadIntelligenceResponse(**intelligence_to_dict(intel))


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

    # Compute intelligence for enriched assist
    lead_full = await conn.fetchrow(
        """SELECT stage, ai_score, deal_amount, stage_updated_at,
                  last_contacted_at, created_at
           FROM leads WHERE id = $1 AND org_id = $2""",
        str(lead_id), org_id,
    )
    intel = compute_lead_intelligence(
        stage=lead_full["stage"] or "new",
        ai_score=lead_full["ai_score"],
        deal_amount=float(lead_full["deal_amount"]) if lead_full["deal_amount"] is not None else None,
        stage_updated_at=lead_full["stage_updated_at"],
        last_contacted_at=lead_full["last_contacted_at"],
        created_at=lead_full["created_at"],
    )

    lead_data = {
        "name": answers.get("name", "there"),
        "stage": lead_row["stage"] or "new",
        "answers": answers,
        "ai_score": lead_row["ai_score"],
        "ai_summary": lead_row["ai_summary"],
        "service": answers.get("service", ""),
        "close_probability": intel.close_probability,
        "days_in_stage": intel.days_in_stage,
        "stage_leak_warning": intel.stage_leak_warning,
        "stage_leak_message": intel.stage_leak_message,
    }

    # Add org conversion context
    from app.services.analytics_service import get_pipeline_metrics
    try:
        pipeline = await get_pipeline_metrics(conn, org_id)
        org_data["conversion_rate"] = pipeline["totals"]["conversion_rate"]
        org_data["avg_days_to_close"] = pipeline["velocity"]["avg_days_to_close"]
    except Exception:
        pass

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


@router.get("/leads/{lead_id}/engagement", response_model=LeadEngagementResponse)
async def get_lead_engagement(
    lead_id: UUID,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Return engagement plan, steps, and events for a lead.
    Returns {plan: null, steps: [], events: []} when no plan exists.
    Never returns 500 — all errors degrade gracefully.
    """
    import json as _json
    import logging as _logging
    _log = _logging.getLogger(__name__)

    lead = await conn.fetchval(
        "SELECT id FROM leads WHERE id = $1 AND org_id = $2",
        str(lead_id), org_id,
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    plan             = None
    steps            = []
    events           = []
    inbound_messages = []

    try:
        # Active plan
        plan_row = await conn.fetchrow(
            """SELECT id, lead_id, org_id, funnel_id, status, current_step,
                      paused, escalation_reason, created_at, updated_at
               FROM engagement_plans
               WHERE lead_id = $1 AND status = 'active'
               ORDER BY created_at DESC LIMIT 1""",
            str(lead_id),
        )

        if plan_row:
            plan = EngagementPlanItem(**dict(plan_row))

            step_rows = await conn.fetch(
                """SELECT id, plan_id, step_order, channel, action_type,
                          scheduled_for, executed_at, status, template_key,
                          generated_content_json, created_at
                   FROM engagement_steps
                   WHERE plan_id = $1
                   ORDER BY step_order ASC""",
                str(plan_row["id"]),
            )
            for r in step_rows:
                try:
                    d = dict(r)
                    gcj = d.get("generated_content_json")
                    if isinstance(gcj, str):
                        try:
                            gcj = _json.loads(gcj)
                        except Exception:
                            gcj = None
                    d["generated_content_json"] = gcj
                    steps.append(EngagementStepItem(**d))
                except Exception as step_exc:
                    _log.warning("Skipping malformed engagement step: %s", step_exc)

        event_rows = await conn.fetch(
            """SELECT id, lead_id, org_id, channel, event_type, direction,
                      content, metadata_json, created_at
               FROM engagement_events
               WHERE lead_id = $1
               ORDER BY created_at ASC""",
            str(lead_id),
        )
        for r in event_rows:
            try:
                d = dict(r)
                mj = d.get("metadata_json")
                if isinstance(mj, str):
                    try:
                        mj = _json.loads(mj)
                    except Exception:
                        mj = None
                d["metadata_json"] = mj
                events.append(EngagementEventItem(**d))
            except Exception as ev_exc:
                _log.warning("Skipping malformed engagement event: %s", ev_exc)

        inbound_rows = await conn.fetch(
            """SELECT id, lead_id, org_id, channel, message_body, classification,
                      suggested_response, metadata_json, created_at
               FROM inbound_messages
               WHERE lead_id = $1
               ORDER BY created_at ASC""",
            str(lead_id),
        )
        for r in inbound_rows:
            try:
                d = dict(r)
                mj = d.get("metadata_json")
                if isinstance(mj, str):
                    try:
                        mj = _json.loads(mj)
                    except Exception:
                        mj = None
                d["metadata_json"] = mj
                inbound_messages.append(InboundMessageItem(**d))
            except Exception as im_exc:
                _log.warning("Skipping malformed inbound message: %s", im_exc)

    except Exception as exc:
        _log.error("Engagement fetch error for lead %s: %s", lead_id, exc)
        # Return empty state rather than 500
        return LeadEngagementResponse(plan=None, steps=[], events=[], inbound_messages=[])

    return LeadEngagementResponse(plan=plan, steps=steps, events=events, inbound_messages=inbound_messages)


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
