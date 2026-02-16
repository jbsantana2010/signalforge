import json
import re
from uuid import UUID

import asyncpg
from fastapi import HTTPException


async def get_funnel_by_slug(conn: asyncpg.Connection, slug: str) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT f.id, f.org_id, f.slug, f.name, f.schema_json, f.languages, f.is_active,
               o.branding
        FROM funnels f
        JOIN orgs o ON o.id = f.org_id
        WHERE f.slug = $1 AND f.is_active = true
        """,
        slug,
    )


def validate_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return len(digits) >= 10


def validate_required_fields(schema_json: dict, answers: dict) -> list[str]:
    """Return list of missing required field keys."""
    missing = []
    for step in schema_json.get("steps", []):
        for field in step.get("fields", []):
            if field.get("required") and field["key"] not in answers:
                missing.append(field["key"])
    return missing


async def submit_lead(
    conn: asyncpg.Connection,
    funnel_slug: str,
    answers: dict,
    language: str,
    source: dict,
) -> UUID:
    funnel = await conn.fetchrow(
        "SELECT id, org_id, schema_json FROM funnels WHERE slug = $1 AND is_active = true",
        funnel_slug,
    )
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")

    schema_json = json.loads(funnel["schema_json"]) if isinstance(funnel["schema_json"], str) else funnel["schema_json"]

    missing = validate_required_fields(schema_json, answers)
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Missing required fields: {', '.join(missing)}"
        )

    phone = answers.get("phone", "")
    if phone and not validate_phone(phone):
        raise HTTPException(status_code=422, detail="Invalid phone number")

    lead_id = await conn.fetchval(
        """
        INSERT INTO leads (org_id, funnel_id, language, answers_json, source_json)
        VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
        RETURNING id
        """,
        funnel["org_id"],
        funnel["id"],
        language,
        json.dumps(answers),
        json.dumps(source),
    )
    return lead_id


async def get_leads(
    conn: asyncpg.Connection,
    org_id: str,
    page: int = 1,
    per_page: int = 20,
    funnel_id: str | None = None,
    language: str | None = None,
    search: str | None = None,
) -> tuple[list[dict], int]:
    conditions = ["l.org_id = $1"]
    params: list = [org_id]
    idx = 2

    if funnel_id:
        conditions.append(f"l.funnel_id = ${idx}")
        params.append(funnel_id)
        idx += 1

    if language:
        conditions.append(f"l.language = ${idx}")
        params.append(language)
        idx += 1

    if search:
        conditions.append(
            f"(l.answers_json->>'name' ILIKE ${idx} OR l.answers_json->>'phone' ILIKE ${idx})"
        )
        params.append(f"%{search}%")
        idx += 1

    where_clause = " AND ".join(conditions)

    count = await conn.fetchval(
        f"SELECT COUNT(*) FROM leads l WHERE {where_clause}", *params
    )

    offset = (page - 1) * per_page
    params.extend([per_page, offset])

    rows = await conn.fetch(
        f"""
        SELECT l.id, l.created_at, l.answers_json, l.language, l.score,
               l.tags, l.priority, l.ai_score
        FROM leads l
        WHERE {where_clause}
        ORDER BY l.created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
    )

    items = []
    for row in rows:
        answers = json.loads(row["answers_json"]) if isinstance(row["answers_json"], str) else row["answers_json"]
        items.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "name": answers.get("name"),
                "phone": answers.get("phone"),
                "service": answers.get("service"),
                "language": row["language"],
                "score": float(row["score"]) if row["score"] is not None else None,
                "tags": list(row["tags"]) if row["tags"] else None,
                "priority": row["priority"],
                "ai_score": row["ai_score"],
            }
        )

    return items, count


async def get_lead_detail(
    conn: asyncpg.Connection, org_id: str, lead_id: str
) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT id, org_id, funnel_id, language, answers_json, source_json,
               score, is_spam, created_at,
               tags, priority, ai_summary, ai_score,
               email_status, sms_status, call_status, call_attempts,
               contact_status, last_contacted_at,
               stage, deal_amount, stage_updated_at
        FROM leads
        WHERE id = $1 AND org_id = $2
        """,
        lead_id,
        org_id,
    )
    if not row:
        return None

    answers = json.loads(row["answers_json"]) if isinstance(row["answers_json"], str) else row["answers_json"]
    source = json.loads(row["source_json"]) if isinstance(row["source_json"], str) else row["source_json"]

    return {
        "id": row["id"],
        "org_id": row["org_id"],
        "funnel_id": row["funnel_id"],
        "language": row["language"],
        "answers_json": answers,
        "source_json": source,
        "score": float(row["score"]) if row["score"] is not None else None,
        "is_spam": row["is_spam"],
        "created_at": row["created_at"],
        "tags": list(row["tags"]) if row["tags"] else None,
        "priority": row["priority"],
        "ai_summary": row["ai_summary"],
        "ai_score": row["ai_score"],
        "email_status": row["email_status"],
        "sms_status": row["sms_status"],
        "call_status": row["call_status"],
        "call_attempts": row["call_attempts"] or 0,
        "contact_status": row["contact_status"],
        "last_contacted_at": row["last_contacted_at"],
        "stage": row["stage"] or "new",
        "deal_amount": float(row["deal_amount"]) if row["deal_amount"] is not None else None,
        "stage_updated_at": row["stage_updated_at"],
    }


async def get_funnels_for_org(conn: asyncpg.Connection, org_id: str) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, slug, name, languages, is_active, created_at
        FROM funnels
        WHERE org_id = $1
        ORDER BY created_at DESC
        """,
        org_id,
    )
    return [dict(row) for row in rows]


async def get_funnel_detail(
    conn: asyncpg.Connection, org_id: str, funnel_id: str
) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT id, org_id, slug, name, schema_json, languages, is_active, created_at,
               routing_rules, auto_email_enabled, auto_sms_enabled, auto_call_enabled,
               notification_emails, webhook_url, rep_phone_number, twilio_from_number,
               working_hours_start, working_hours_end,
               sequence_enabled, sequence_config
        FROM funnels
        WHERE id = $1 AND org_id = $2
        """,
        funnel_id,
        org_id,
    )
    if not row:
        return None

    schema_json = json.loads(row["schema_json"]) if isinstance(row["schema_json"], str) else row["schema_json"]
    routing_rules = (
        json.loads(row["routing_rules"])
        if isinstance(row["routing_rules"], str)
        else row["routing_rules"]
    ) if row["routing_rules"] else None

    return {
        "id": row["id"],
        "org_id": row["org_id"],
        "slug": row["slug"],
        "name": row["name"],
        "schema_json": schema_json,
        "languages": list(row["languages"]) if row["languages"] else ["en"],
        "is_active": row["is_active"],
        "created_at": row["created_at"],
        "routing_rules": routing_rules,
        "auto_email_enabled": row["auto_email_enabled"] or False,
        "auto_sms_enabled": row["auto_sms_enabled"] or False,
        "auto_call_enabled": row["auto_call_enabled"] or False,
        "notification_emails": list(row["notification_emails"]) if row["notification_emails"] else None,
        "webhook_url": row["webhook_url"],
        "rep_phone_number": row["rep_phone_number"],
        "twilio_from_number": row["twilio_from_number"],
        "working_hours_start": row["working_hours_start"] or 9,
        "working_hours_end": row["working_hours_end"] or 19,
        "sequence_enabled": row["sequence_enabled"] or False,
        "sequence_config": (
            json.loads(row["sequence_config"])
            if isinstance(row["sequence_config"], str)
            else row["sequence_config"]
        ) if row["sequence_config"] else None,
    }


async def update_funnel_settings(
    conn: asyncpg.Connection, org_id: str, funnel_id: str, updates: dict
) -> dict | None:
    # Verify funnel belongs to org
    exists = await conn.fetchval(
        "SELECT id FROM funnels WHERE id = $1 AND org_id = $2",
        funnel_id,
        org_id,
    )
    if not exists:
        return None

    # Build dynamic SET clause from non-None updates
    set_parts = []
    params = []
    idx = 1

    column_map = {
        "routing_rules": "routing_rules",
        "auto_email_enabled": "auto_email_enabled",
        "auto_sms_enabled": "auto_sms_enabled",
        "auto_call_enabled": "auto_call_enabled",
        "notification_emails": "notification_emails",
        "webhook_url": "webhook_url",
        "rep_phone_number": "rep_phone_number",
        "twilio_from_number": "twilio_from_number",
        "working_hours_start": "working_hours_start",
        "working_hours_end": "working_hours_end",
        "sequence_enabled": "sequence_enabled",
        "sequence_config": "sequence_config",
    }

    for field, column in column_map.items():
        if field in updates and updates[field] is not None:
            value = updates[field]
            if field in ("routing_rules", "sequence_config"):
                set_parts.append(f"{column} = ${idx}::jsonb")
                params.append(json.dumps(value))
            else:
                set_parts.append(f"{column} = ${idx}")
                params.append(value)
            idx += 1

    if not set_parts:
        return await get_funnel_detail(conn, org_id, funnel_id)

    params.append(funnel_id)
    params.append(org_id)

    await conn.execute(
        f"""
        UPDATE funnels
        SET {', '.join(set_parts)}
        WHERE id = ${idx} AND org_id = ${idx + 1}
        """,
        *params,
    )

    return await get_funnel_detail(conn, org_id, funnel_id)


async def get_lead_sequences(conn, lead_id: str) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, step, scheduled_at, sent_at, status, message
        FROM lead_sequences
        WHERE lead_id = $1
        ORDER BY step
        """,
        lead_id,
    )
    return [dict(r) for r in rows]
