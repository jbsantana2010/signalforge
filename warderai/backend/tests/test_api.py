"""
API tests for LeadForge backend.

These tests mock the database layer so they can run without a live Postgres instance.
Run with: pytest tests/test_api.py -v
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_conn():
    """Create a mock asyncpg connection."""
    conn = AsyncMock()
    return conn


@pytest.fixture
def sample_funnel_row():
    org_id = uuid4()
    funnel_id = uuid4()
    schema_json = json.dumps({
        "slug": "solar-prime",
        "languages": ["en", "es"],
        "steps": [
            {
                "id": "service",
                "title": {"en": "What do you need?"},
                "fields": [
                    {
                        "key": "service",
                        "type": "select",
                        "required": True,
                        "label": {"en": "Service"},
                        "options": [
                            {"value": "solar", "label": {"en": "Solar Installation"}},
                        ],
                    }
                ],
            },
            {
                "id": "contact_info",
                "title": {"en": "Your Information"},
                "fields": [
                    {"key": "name", "type": "text", "required": True, "label": {"en": "Full Name"}},
                    {"key": "zip_code", "type": "text", "required": True, "label": {"en": "Zip Code"}},
                ],
            },
            {
                "id": "phone_info",
                "title": {"en": "Contact"},
                "fields": [
                    {"key": "phone", "type": "tel", "required": True, "label": {"en": "Phone"}},
                    {"key": "contact_time", "type": "select", "required": True, "label": {"en": "Contact Time"},
                     "options": [{"value": "morning", "label": {"en": "Morning"}}]},
                ],
            },
        ],
    })
    branding = json.dumps({"primary_color": "#f59e0b"})
    return {
        "id": funnel_id,
        "org_id": org_id,
        "slug": "solar-prime",
        "name": "Solar Prime Lead Funnel",
        "schema_json": schema_json,
        "languages": ["en", "es"],
        "is_active": True,
        "branding": branding,
    }


@pytest.fixture
def sample_funnel_row_for_submit(sample_funnel_row):
    """Subset of columns returned by submit_lead's query."""
    return {
        "id": sample_funnel_row["id"],
        "org_id": sample_funnel_row["org_id"],
        "schema_json": sample_funnel_row["schema_json"],
    }


def make_mock_record(data: dict):
    """Create a mock that behaves like an asyncpg.Record."""
    record = MagicMock()
    record.__getitem__ = lambda self, key: data[key]
    record.__contains__ = lambda self, key: key in data
    record.keys = lambda: data.keys()
    record.values = lambda: data.values()
    record.items = lambda: data.items()
    return record


@pytest.fixture
def override_db(mock_conn):
    """Override the get_db dependency with our mock connection."""
    from app.database import get_db

    async def _override():
        yield mock_conn

    app.dependency_overrides[get_db] = _override
    yield mock_conn
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_funnel_returns_200(override_db, sample_funnel_row):
    override_db.fetchrow = AsyncMock(return_value=make_mock_record(sample_funnel_row))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/public/funnels/solar-prime")

    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "solar-prime"
    assert body["name"] == "Solar Prime Lead Funnel"
    assert "steps" in body["schema_json"]


@pytest.mark.asyncio
async def test_get_funnel_not_found(override_db):
    override_db.fetchrow = AsyncMock(return_value=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/public/funnels/nonexistent")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_lead_valid(override_db, sample_funnel_row_for_submit):
    lead_id = uuid4()
    override_db.fetchrow = AsyncMock(return_value=make_mock_record(sample_funnel_row_for_submit))
    override_db.fetchval = AsyncMock(return_value=lead_id)

    payload = {
        "funnel_slug": "solar-prime",
        "answers": {
            "service": "solar",
            "zip_code": "90210",
            "name": "Jane Doe",
            "phone": "3105551234",
            "contact_time": "morning",
        },
        "language": "en",
        "source": {"utm_source": "test"},
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/public/leads/submit", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


@pytest.mark.asyncio
async def test_submit_lead_honeypot_rejected(override_db):
    """Honeypot filled -> 200 OK but silently rejected (no DB call)."""
    payload = {
        "funnel_slug": "solar-prime",
        "answers": {"service": "solar", "name": "Bot", "phone": "1234567890", "zip_code": "00000", "contact_time": "morning"},
        "language": "en",
        "honeypot": "I am a bot",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/public/leads/submit", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # The DB should NOT have been called since honeypot was detected
    override_db.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_admin_leads_no_auth():
    """GET /admin/leads without auth returns 403 (HTTPBearer returns 403 for missing credentials)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/leads")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_login_and_get_leads(override_db):
    """Login then access /admin/leads with the token."""
    user_id = uuid4()
    org_id = uuid4()

    from app.core.security import hash_password

    pw_hash = hash_password("admin123")

    user_record = make_mock_record({
        "id": user_id,
        "org_id": org_id,
        "password_hash": pw_hash,
    })

    # First call = login query, second call = leads count, third = leads fetch
    lead_id = uuid4()
    now = datetime.now(timezone.utc)
    lead_row = make_mock_record({
        "id": lead_id,
        "created_at": now,
        "answers_json": json.dumps({"name": "Test", "phone": "1234567890", "service": "solar"}),
        "language": "en",
        "score": None,
    })

    override_db.fetchrow = AsyncMock(return_value=user_record)
    override_db.fetchval = AsyncMock(return_value=1)
    override_db.fetch = AsyncMock(return_value=[lead_row])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login
        login_resp = await client.post("/admin/auth/login", json={
            "email": "admin@solarprime.com",
            "password": "admin123",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        # Get leads
        leads_resp = await client.get(
            "/admin/leads",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert leads_resp.status_code == 200
        body = leads_resp.json()
        assert "leads" in body
        assert body["total"] == 1
