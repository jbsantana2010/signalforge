import asyncpg
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models.schemas import LeadSubmitRequest, LeadSubmitResponse
from app.services.lead_service import submit_lead

router = APIRouter()


@router.post("/leads/submit", response_model=LeadSubmitResponse)
async def submit(
    payload: LeadSubmitRequest,
    conn: asyncpg.Connection = Depends(get_db),
):
    # Honeypot check: silently reject if honeypot field is filled
    if payload.honeypot:
        return LeadSubmitResponse(success=True, message="Thank you for your submission!")

    await submit_lead(
        conn=conn,
        funnel_slug=payload.funnel_slug,
        answers=payload.answers,
        language=payload.language,
        source=payload.source,
    )

    return LeadSubmitResponse(success=True, message="Thank you for your submission!")
