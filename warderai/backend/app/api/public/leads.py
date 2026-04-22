import json

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.database import get_db
from app.models.schemas import LeadSubmitRequest, LeadSubmitResponse
from app.services.lead_service import submit_lead

router = APIRouter()


@router.post("/leads/submit", response_model=LeadSubmitResponse)
async def submit(
    payload: LeadSubmitRequest,
    background_tasks: BackgroundTasks,
    conn: asyncpg.Connection = Depends(get_db),
):
    # Honeypot check: silently reject if honeypot field is filled
    if payload.honeypot:
        return LeadSubmitResponse(success=True, message="Thank you for your submission!")

    lead_id = await submit_lead(
        conn=conn,
        funnel_slug=payload.funnel_slug,
        answers=payload.answers,
        language=payload.language,
        source=payload.source,
    )

    # Enqueue automation processing as a background task
    from app.services.automation_service import process_automation
    import app.database as database_module
    background_tasks.add_task(process_automation, str(lead_id), database_module.pool)

    return LeadSubmitResponse(success=True, message="Thank you for your submission!")


@router.post("/leads/basin")
async def basin_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    conn: asyncpg.Connection = Depends(get_db),
):
    """Receive Basin form submissions from warderai.com and create leads in Warder pipeline."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Safe field extraction — unknown fields are ignored
    name = body.get("name", "") or ""
    email = body.get("email", "") or ""
    phone = body.get("phone", "") or ""
    company = body.get("company", "") or ""
    website = body.get("website", "") or ""
    message = body.get("message", "") or ""
    lang = body.get("lang", "") or "en"
    page = body.get("page", "") or ""
    referrer = body.get("referrer", "") or ""
    timestamp = body.get("timestamp", "") or ""

    # Resolve Warder org
    org = await conn.fetchrow("SELECT id FROM orgs WHERE slug = $1", "warder")
    if not org:
        raise HTTPException(status_code=404, detail="Org 'warder' not found")

    # Resolve website-demo funnel within Warder org
    funnel = await conn.fetchrow(
        "SELECT id FROM funnels WHERE org_id = $1 AND slug = $2 AND is_active = true",
        org["id"],
        "website-demo",
    )
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel 'website-demo' not found in org 'warder'")

    # Idempotency: skip duplicate if same email+name arrived within 5 minutes
    if email and name:
        existing = await conn.fetchval(
            """
            SELECT id FROM leads
            WHERE org_id = $1
              AND answers_json->>'email' = $2
              AND answers_json->>'name' = $3
              AND created_at > NOW() - INTERVAL '5 minutes'
            LIMIT 1
            """,
            org["id"],
            email,
            name,
        )
        if existing:
            return {"status": "duplicate_ignored"}

    answers = {
        "name": name,
        "phone": phone,
        "email": email,
        "company": company,
        "website": website,
        "message": message,
    }
    source = {
        "source": "warderai.com",
        "channel": "website",
        "form_type": "demo_request",
        "page": page,
        "referrer": referrer,
        "timestamp": timestamp,
    }

    lead_id = await conn.fetchval(
        """
        INSERT INTO leads (org_id, funnel_id, language, answers_json, source_json)
        VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
        RETURNING id
        """,
        org["id"],
        funnel["id"],
        lang,
        json.dumps(answers),
        json.dumps(source),
    )

    from app.services.automation_service import process_automation
    import app.database as database_module
    background_tasks.add_task(process_automation, str(lead_id), database_module.pool)

    return {
        "status": "ok",
        "lead_id": str(lead_id),
        "org_slug": "warder",
        "funnel_slug": "website-demo",
    }
