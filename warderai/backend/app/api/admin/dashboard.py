"""Admin dashboard endpoints."""

import json
import os

import asyncpg
import httpx
from fastapi import APIRouter, Depends

from app.core.auth import resolve_active_org_id
from app.database import get_db
from app.models.schemas import OrgInsightsResponse, PipelineMetricsResponse
from app.services.analytics_service import get_org_dashboard_metrics, get_pipeline_metrics

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    metrics = await get_org_dashboard_metrics(conn, org_id)
    return {"metrics": metrics}


@router.get("/dashboard/metrics", response_model=PipelineMetricsResponse)
async def dashboard_metrics(
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """Pipeline metrics for the org dashboard (Sprint 7)."""
    data = await get_pipeline_metrics(conn, org_id)
    return data


@router.get("/dashboard/insights", response_model=OrgInsightsResponse)
async def dashboard_insights(
    org_id: str = Depends(resolve_active_org_id),
    conn: asyncpg.Connection = Depends(get_db),
):
    """AI-powered strategic insights for the org dashboard (Sprint 8)."""
    pipeline = await get_pipeline_metrics(conn, org_id)
    dash = await get_org_dashboard_metrics(conn, org_id)

    # Build context for insights
    context = {
        "total_leads": dash["total_leads"],
        "leads_7d": dash["leads_last_7_days"],
        "conversion_rate": pipeline["totals"]["conversion_rate"],
        "won": pipeline["totals"]["won"],
        "lost": pipeline["totals"]["lost"],
        "pipeline_value": pipeline["pipeline"]["total_value"],
        "won_value": pipeline["pipeline"]["won_value"],
        "avg_days_to_close": pipeline["velocity"]["avg_days_to_close"],
        "overdue_actions": pipeline["actionability"]["overdue_next_actions"],
        "stale_leads": pipeline["actionability"]["stale_leads"],
        "contacted_percent": dash["contacted_percent"],
        "actual_revenue": dash["actual_revenue"],
    }

    api_key = os.getenv("CLAUDE_API_KEY", "")
    if api_key:
        try:
            return await _generate_ai_insights(api_key, context)
        except Exception:
            pass

    return _generate_stub_insights(context)


def _generate_stub_insights(ctx: dict) -> OrgInsightsResponse:
    """Deterministic insights from pipeline data."""
    highlights = []

    if ctx["leads_7d"] > 0:
        highlights.append(f"{ctx['leads_7d']} new leads in the last 7 days")

    if ctx["conversion_rate"] > 0:
        highlights.append(f"Conversion rate: {ctx['conversion_rate']}%")

    if ctx["overdue_actions"] > 0:
        highlights.append(f"{ctx['overdue_actions']} overdue actions need attention")

    if ctx["stale_leads"] > 0:
        highlights.append(f"{ctx['stale_leads']} stale leads at risk of loss")

    if ctx["pipeline_value"] > 0:
        highlights.append(f"Active pipeline: ${ctx['pipeline_value']:,.0f}")

    if ctx["won_value"] > 0:
        highlights.append(f"Revenue won: ${ctx['won_value']:,.0f}")

    if not highlights:
        highlights.append("No pipeline activity yet — start by adding leads")

    # Summary
    parts = []
    if ctx["total_leads"] > 0:
        parts.append(f"You have {ctx['total_leads']} total leads")
        if ctx["conversion_rate"] > 0:
            parts.append(f"with a {ctx['conversion_rate']}% conversion rate")
    if ctx["overdue_actions"] > 0:
        parts.append(f"{ctx['overdue_actions']} actions are overdue")
    if ctx["stale_leads"] > 0:
        parts.append(f"{ctx['stale_leads']} leads are going stale")

    summary = ". ".join(parts) + "." if parts else "No data available yet."

    return OrgInsightsResponse(summary=summary, highlights=highlights, mode="stub")


async def _generate_ai_insights(api_key: str, ctx: dict) -> OrgInsightsResponse:
    """AI-powered strategic insights via Claude."""
    prompt = (
        "You are a sales analytics advisor. Based on the following pipeline data, "
        "generate strategic insights.\n\n"
        f"Pipeline data: {json.dumps(ctx)}\n\n"
        "Return a JSON object with:\n"
        "- \"summary\": 2-3 sentence strategic overview\n"
        "- \"highlights\": array of 3-5 actionable insight strings (each under 80 chars)\n\n"
        "Focus on actionable recommendations. Be specific with numbers.\n\n"
        "Respond with ONLY valid JSON, no other text."
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["content"][0]["text"]
        result = json.loads(text)
        return OrgInsightsResponse(
            summary=result["summary"],
            highlights=result["highlights"],
            mode="claude",
        )
