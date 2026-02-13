"""Analytics service – computes dashboard metrics from lead data."""

import asyncpg


async def get_org_dashboard_metrics(conn: asyncpg.Connection, org_id: str) -> dict:
    """Return dashboard metrics for a single org."""

    # Org-level revenue settings
    org_row = await conn.fetchrow(
        "SELECT avg_deal_value, close_rate_percent FROM orgs WHERE id = $1",
        org_id,
    )
    avg_deal_value = float(org_row["avg_deal_value"] or 0) if org_row else 0
    close_rate = float(org_row["close_rate_percent"] or 0) if org_row else 0

    # Lead counts
    total_leads = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1", org_id
    )

    leads_7d = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND created_at >= NOW() - INTERVAL '7 days'",
        org_id,
    )

    # Contacted %
    contacted = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND contact_status IS NOT NULL AND contact_status != ''",
        org_id,
    )
    contacted_percent = round((contacted / total_leads * 100), 1) if total_leads else 0

    # AI score distribution
    ai_hot = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND ai_score >= 70", org_id
    )
    ai_warm = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND ai_score >= 40 AND ai_score < 70",
        org_id,
    )
    ai_cold = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND ai_score IS NOT NULL AND ai_score < 40",
        org_id,
    )

    # Average response time (seconds between lead created and first contact)
    avg_resp = await conn.fetchval(
        """SELECT AVG(EXTRACT(EPOCH FROM (last_contacted_at - created_at)))
           FROM leads
           WHERE org_id = $1 AND last_contacted_at IS NOT NULL""",
        org_id,
    )
    avg_response_seconds = round(float(avg_resp), 1) if avg_resp else None

    # Call connect rate
    total_calls = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND call_status IS NOT NULL AND call_status != ''",
        org_id,
    )
    connected_calls = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND call_status = 'completed'",
        org_id,
    )
    call_connect_rate = round((connected_calls / total_calls * 100), 1) if total_calls else 0

    # Estimated revenue
    estimated_revenue = round(total_leads * (close_rate / 100) * avg_deal_value, 2)

    return {
        "total_leads": total_leads,
        "leads_last_7_days": leads_7d,
        "avg_response_seconds": avg_response_seconds,
        "contacted_percent": contacted_percent,
        "ai_hot_count": ai_hot,
        "ai_warm_count": ai_warm,
        "ai_cold_count": ai_cold,
        "call_connect_rate": call_connect_rate,
        "estimated_revenue": estimated_revenue,
        "avg_deal_value": avg_deal_value,
        "close_rate_percent": close_rate,
    }
