"""Analytics service – computes dashboard metrics from lead data."""

import json

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

    # Pipeline metrics (actual revenue tracking)
    actual_revenue_raw = await conn.fetchval(
        "SELECT COALESCE(SUM(deal_amount), 0) FROM leads WHERE org_id = $1 AND stage = 'won'",
        org_id,
    )
    actual_revenue = round(float(actual_revenue_raw), 2)

    won_deals = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND stage = 'won'",
        org_id,
    )

    lost_deals = await conn.fetchval(
        "SELECT COUNT(*) FROM leads WHERE org_id = $1 AND stage = 'lost'",
        org_id,
    )

    closed_total = won_deals + lost_deals
    actual_close_rate = round((won_deals / closed_total * 100), 1) if closed_total > 0 else 0

    pipeline_value_raw = await conn.fetchval(
        "SELECT COALESCE(SUM(deal_amount), 0) FROM leads WHERE org_id = $1 AND stage IN ('qualified', 'proposal')",
        org_id,
    )
    pipeline_value = round(float(pipeline_value_raw), 2)

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
        "actual_revenue": actual_revenue,
        "actual_close_rate": actual_close_rate,
        "won_deals": won_deals,
        "lost_deals": lost_deals,
        "pipeline_value": pipeline_value,
    }


async def get_pipeline_metrics(conn: asyncpg.Connection, org_id: str) -> dict:
    """Return structured pipeline metrics for the Sprint 7 dashboard.

    Uses 5 queries:
      1. Stage counts + totals + pipeline values (single aggregation query)
      2. Avg days to close (from lead_stage_history)
      3. Avg days in stage (window function over stage history)
      4. Overdue next-action count
      5. Stale leads count (no contact in 7 days)
    """

    STAGES = ["new", "contacted", "qualified", "proposal", "won", "lost"]
    STALE_DAYS = 7

    # --- Query 1: stage counts + values in one pass ---
    rows = await conn.fetch(
        """
        SELECT
            COALESCE(stage, 'new') AS stage,
            COUNT(*)               AS cnt,
            COALESCE(SUM(deal_amount), 0) AS stage_value
        FROM leads
        WHERE org_id = $1
        GROUP BY COALESCE(stage, 'new')
        """,
        org_id,
    )
    stage_counts: dict[str, int] = {s: 0 for s in STAGES}
    stage_values: dict[str, float] = {s: 0.0 for s in STAGES}
    for r in rows:
        s = r["stage"]
        if s in stage_counts:
            stage_counts[s] = int(r["cnt"])
            stage_values[s] = float(r["stage_value"])

    total = sum(stage_counts.values())
    won = stage_counts["won"]
    lost = stage_counts["lost"]
    conversion_rate = round(won / total * 100, 1) if total > 0 else 0.0

    # pipeline_value = qualified + proposal (active pipeline, excludes won)
    pipeline_total = stage_values["qualified"] + stage_values["proposal"]
    won_value = stage_values["won"]

    # avg_deal_value: average across won deals only (most meaningful)
    avg_deal_raw = await conn.fetchval(
        "SELECT AVG(deal_amount) FROM leads WHERE org_id = $1 AND stage = 'won' AND deal_amount IS NOT NULL",
        org_id,
    )
    avg_deal = round(float(avg_deal_raw), 2) if avg_deal_raw else 0.0

    # --- Query 2: avg days to close ---
    # For each won lead, find the earliest history row where to_stage='won',
    # then compute days from lead.created_at to that timestamp.
    avg_close_raw = await conn.fetchval(
        """
        SELECT AVG(EXTRACT(EPOCH FROM (h.won_at - l.created_at)) / 86400.0)
        FROM leads l
        JOIN (
            SELECT lead_id, MIN(created_at) AS won_at
            FROM lead_stage_history
            WHERE org_id = $1 AND to_stage = 'won'
            GROUP BY lead_id
        ) h ON h.lead_id = l.id
        WHERE l.org_id = $1 AND l.stage = 'won'
        """,
        org_id,
    )
    avg_days_to_close = round(float(avg_close_raw), 1) if avg_close_raw else None

    # --- Query 3: avg days in stage (window function) ---
    # For each transition, compute time from when a lead entered a stage to
    # when it left (next transition). For the current stage, use now() as end.
    # Bounded to last 90 days of history for performance.
    stage_duration_rows = await conn.fetch(
        """
        WITH transitions AS (
            SELECT
                lead_id,
                to_stage AS stage,
                created_at AS entered_at,
                LEAD(created_at) OVER (PARTITION BY lead_id ORDER BY created_at) AS left_at
            FROM lead_stage_history
            WHERE org_id = $1
              AND created_at >= NOW() - INTERVAL '90 days'
        )
        SELECT
            stage,
            AVG(EXTRACT(EPOCH FROM (COALESCE(left_at, NOW()) - entered_at)) / 86400.0) AS avg_days
        FROM transitions
        WHERE stage IN ('new', 'contacted', 'qualified', 'proposal')
        GROUP BY stage
        """,
        org_id,
    )
    avg_days_in_stage: dict[str, float | None] = {
        "new": None, "contacted": None, "qualified": None, "proposal": None,
    }
    for r in stage_duration_rows:
        avg_days_in_stage[r["stage"]] = round(float(r["avg_days"]), 1)

    # --- Query 4: overdue next actions ---
    overdue = await conn.fetchval(
        """
        SELECT COUNT(*) FROM leads
        WHERE org_id = $1
          AND next_action_at IS NOT NULL
          AND next_action_at < NOW()
          AND stage NOT IN ('won', 'lost')
        """,
        org_id,
    )

    # --- Query 5: stale leads (no contact in 7 days) ---
    stale = await conn.fetchval(
        """
        SELECT COUNT(*) FROM leads
        WHERE org_id = $1
          AND stage NOT IN ('won', 'lost')
          AND (
              (last_contacted_at IS NULL AND created_at < NOW() - INTERVAL '%s days')
              OR last_contacted_at < NOW() - INTERVAL '%s days'
          )
        """ % (STALE_DAYS, STALE_DAYS),
        org_id,
    )

    return {
        "totals": {
            "leads": total,
            "won": won,
            "lost": lost,
            "conversion_rate": conversion_rate,
        },
        "stages": stage_counts,
        "pipeline": {
            "total_value": round(pipeline_total, 2),
            "won_value": round(won_value, 2),
            "avg_deal_value": avg_deal,
        },
        "velocity": {
            "avg_days_to_close": avg_days_to_close,
            "avg_days_in_stage": avg_days_in_stage,
        },
        "actionability": {
            "overdue_next_actions": int(overdue),
            "stale_leads": int(stale),
        },
    }


async def get_campaign_metrics(conn: asyncpg.Connection, org_id: str) -> dict:
    """Return per-campaign attribution metrics for an org."""

    # Org-level revenue settings
    org_row = await conn.fetchrow(
        "SELECT avg_deal_value, close_rate_percent FROM orgs WHERE id = $1",
        org_id,
    )
    avg_deal_value = float(org_row["avg_deal_value"] or 0) if org_row else 0
    close_rate = float(org_row["close_rate_percent"] or 0) if org_row else 0

    rows = await conn.fetch(
        """
        SELECT
            c.id,
            c.campaign_name,
            c.source,
            c.utm_campaign,
            c.ad_spend,
            COUNT(l.id)                                             AS leads,
            COALESCE(AVG(l.ai_score), 0)                            AS avg_ai_score,
            COUNT(l.id) FILTER (WHERE l.stage = 'won')              AS won_deals,
            COALESCE(SUM(l.deal_amount) FILTER (WHERE l.stage = 'won'), 0) AS actual_revenue
        FROM campaigns c
        LEFT JOIN leads l
            ON l.org_id = c.org_id
           AND l.source_json->>'utm_campaign' = c.utm_campaign
        WHERE c.org_id = $1
        GROUP BY c.id, c.campaign_name, c.source, c.utm_campaign, c.ad_spend
        ORDER BY c.created_at DESC
        """,
        org_id,
    )

    campaigns = []
    for r in rows:
        leads = int(r["leads"])
        ad_spend = float(r["ad_spend"])
        avg_ai = round(float(r["avg_ai_score"]), 1)
        est_revenue = round(leads * (close_rate / 100) * avg_deal_value, 2)
        cpl = round(ad_spend / leads, 2) if leads > 0 else None
        roas = round(est_revenue / ad_spend, 2) if ad_spend > 0 else None
        won = int(r["won_deals"])
        act_revenue = round(float(r["actual_revenue"]), 2)
        actual_roas = round(act_revenue / ad_spend, 2) if ad_spend > 0 else None

        campaigns.append({
            "id": str(r["id"]),
            "campaign_name": r["campaign_name"],
            "source": r["source"],
            "utm_campaign": r["utm_campaign"],
            "leads": leads,
            "avg_ai_score": avg_ai,
            "estimated_revenue": est_revenue,
            "ad_spend": ad_spend,
            "cost_per_lead": cpl,
            "roas": roas,
            "won_deals": won,
            "actual_revenue": act_revenue,
            "actual_roas": actual_roas,
        })

    return {"campaigns": campaigns}
