import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends

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
