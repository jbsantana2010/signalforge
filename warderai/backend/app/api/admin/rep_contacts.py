"""
Admin Rep Contacts API: manage rep contact profiles for notification routing.
Org-scoped — requires JWT Bearer + X-ORG-ID.

Endpoints:
  GET  /admin/rep-contacts         — list all contacts for current org
  POST /admin/rep-contacts         — create or upsert by email
  PATCH /admin/rep-contacts/{id}   — update phone / full_name / is_active
"""

import logging
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import resolve_active_org_id
from app.database import get_db
from app.models.schemas import (
    RepContactItem,
    RepContactListResponse,
    RepContactPatchRequest,
    RepContactUpsertRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/rep-contacts", response_model=RepContactListResponse)
async def list_rep_contacts(
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Return all rep contacts for the current org."""
    rows = await conn.fetch(
        """
        SELECT id, org_id, email, phone, full_name, is_active, created_at
        FROM rep_contacts
        WHERE org_id = $1
        ORDER BY created_at ASC
        """,
        org_id,
    )
    contacts = [RepContactItem(**dict(r)) for r in rows]
    return RepContactListResponse(contacts=contacts)


@router.post("/rep-contacts", response_model=RepContactItem, status_code=201)
async def upsert_rep_contact(
    body: RepContactUpsertRequest,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """
    Create or upsert a rep contact by email.
    If a contact with the same org_id + email already exists it is updated.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO rep_contacts (org_id, email, phone, full_name, is_active)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (org_id, email) DO UPDATE
            SET phone      = EXCLUDED.phone,
                full_name  = EXCLUDED.full_name,
                is_active  = EXCLUDED.is_active,
                updated_at = now()
        RETURNING id, org_id, email, phone, full_name, is_active, created_at
        """,
        org_id,
        body.email,
        body.phone,
        body.full_name,
        body.is_active,
    )
    return RepContactItem(**dict(row))


@router.patch("/rep-contacts/{contact_id}", response_model=RepContactItem)
async def patch_rep_contact(
    contact_id: UUID,
    body: RepContactPatchRequest,
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Update phone, full_name, or is_active for a rep contact."""
    existing = await conn.fetchrow(
        "SELECT id FROM rep_contacts WHERE id = $1 AND org_id = $2",
        contact_id, org_id,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rep contact not found")

    row = await conn.fetchrow(
        """
        UPDATE rep_contacts
        SET phone      = COALESCE($1, phone),
            full_name  = COALESCE($2, full_name),
            is_active  = COALESCE($3, is_active),
            updated_at = now()
        WHERE id = $4 AND org_id = $5
        RETURNING id, org_id, email, phone, full_name, is_active, created_at
        """,
        body.phone,
        body.full_name,
        body.is_active,
        contact_id,
        org_id,
    )
    return RepContactItem(**dict(row))
