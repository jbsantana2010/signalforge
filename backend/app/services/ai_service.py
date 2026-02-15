"""
AI service: generates lead scoring and summary using Claude API or deterministic stub.
"""

import json
import os

import httpx


async def generate_ai_summary(answers: dict, scoring_config: dict | None = None) -> tuple[int, str]:
    """
    If CLAUDE_API_KEY env var set: call Claude API, parse {"score": int, "summary": "..."}
    If not set: deterministic stub based on service type.
    scoring_config is an optional org-level rubric from industry templates.
    Returns: (score, summary)
    """
    api_key = os.getenv("CLAUDE_API_KEY", "")

    if api_key:
        return await _call_claude(api_key, answers, scoring_config)

    return _deterministic_stub(answers, scoring_config)


def _deterministic_stub(answers: dict, scoring_config: dict | None = None) -> tuple[int, str]:
    service = answers.get("service", "")
    name = answers.get("name", "Unknown")
    zip_code = answers.get("zip_code", "N/A")
    phone = answers.get("phone", "N/A")

    if service == "solar":
        score = 80
    elif service in ("buy", "sell"):
        score = 70
    else:
        score = 60

    # Adjust score based on scoring_config hints (if present)
    if scoring_config:
        timeframe = answers.get("timeframe", "")
        if timeframe == "immediate":
            score = min(100, score + 10)
        elif timeframe in ("browsing", "planning"):
            score = max(0, score - 10)

    summary = (
        f"Lead from {name} in zip {zip_code}. "
        f"Interested in: {service or 'unknown'}. "
        f"Contact phone: {phone}."
    )

    return score, summary


async def _call_claude(api_key: str, answers: dict, scoring_config: dict | None = None) -> tuple[int, str]:
    scoring_instruction = ""
    if scoring_config:
        scoring_instruction = (
            f"\n\nUse this scoring rubric as guidance: {json.dumps(scoring_config)}\n"
        )

    prompt = (
        "You are a lead scoring assistant. Given the following lead form answers, "
        "return a JSON object with exactly two keys: \"score\" (integer 0-100 indicating "
        "lead quality) and \"summary\" (2-3 sentence summary of the lead).\n\n"
        f"Answers: {json.dumps(answers)}\n"
        f"{scoring_instruction}\n"
        "Respond with ONLY valid JSON, no other text."
    )

    try:
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
                    "max_tokens": 256,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
            result = json.loads(text)
            return int(result["score"]), str(result["summary"])
    except Exception:
        # Fall back to deterministic stub on any failure
        return _deterministic_stub(answers, scoring_config)


# ---------------------------------------------------------------------------
# Ad Strategy Generation
# ---------------------------------------------------------------------------

_INDUSTRY_STUBS: dict[str, dict] = {
    "marine_dealer": {
        "angles": [
            "Dream boat lifestyle — freedom on the water",
            "Trade-in upgrade path — your current boat is worth more than you think",
            "Financing made simple — affordable monthly payments",
            "Seasonal urgency — best selection available now",
        ],
        "hooks": [
            "Your dream boat is closer than you think.",
            "What if your next weekend looked like this?",
            "Trade in your current boat and upgrade today.",
            "Pre-approved financing in under 5 minutes.",
            "This season's best inventory is going fast.",
            "Stop scrolling. Start boating.",
        ],
        "offers": [
            "Free trade-in appraisal — no obligation",
            "Pre-approval in minutes with 0% down options",
            "Exclusive VIP showing for serious buyers",
        ],
        "targeting": [
            "Homeowners 30-65 within 50mi of waterways",
            "Fishing and boating enthusiast audiences",
            "Lookalike audience from past buyers",
            "Retarget website visitors who viewed inventory",
        ],
        "ads": [
            {
                "primary_text": "Your weekends deserve an upgrade. Browse our curated selection of boats — from fishing rigs to family cruisers. Get pre-approved in minutes and hit the water this season.",
                "headline": "Find Your Perfect Boat Today",
                "cta": "Browse Inventory",
            },
            {
                "primary_text": "Thinking about upgrading? Your current boat may be worth more than you think. Get a free trade-in appraisal and see what you qualify for.",
                "headline": "Free Trade-In Appraisal",
                "cta": "Get Your Value",
            },
            {
                "primary_text": "Affordable financing options with rates as low as 4.99%. Pre-qualify in under 5 minutes — no impact to your credit score.",
                "headline": "Low Monthly Payments Available",
                "cta": "Check Your Rate",
            },
        ],
    },
    "equipment_dealer": {
        "angles": [
            "Productivity multiplier — the right equipment pays for itself",
            "Rent vs. buy analysis — which saves you more?",
            "Fleet upgrade — reduce downtime with newer machines",
            "Job-matched equipment — get exactly what the project needs",
        ],
        "hooks": [
            "The right machine can cut your project time in half.",
            "Stop renting. Start owning. See the math.",
            "Equipment downtime is costing you thousands.",
            "New inventory just arrived — commercial and industrial.",
            "Get a quote in 24 hours. Delivered to your site.",
            "Your competitors are already upgrading. Are you?",
        ],
        "offers": [
            "Free job-site consultation and equipment recommendation",
            "Rent-to-own programs with flexible terms",
            "Volume discount for fleet purchases",
        ],
        "targeting": [
            "Construction company owners and fleet managers",
            "Commercial contractors within 100mi radius",
            "Lookalike audience from past equipment buyers",
            "Retarget visitors who viewed specific equipment categories",
        ],
        "ads": [
            {
                "primary_text": "Get the equipment your job demands — excavators, loaders, and more. Free job-site consultation to match you with the right machine.",
                "headline": "Equipment That Performs",
                "cta": "Get a Quote",
            },
            {
                "primary_text": "Renting is burning cash. Our rent-to-own programs let you build equity while you work. Flexible terms for any project size.",
                "headline": "Rent-to-Own Available",
                "cta": "See Options",
            },
            {
                "primary_text": "Reduce downtime and increase productivity with newer, reliable equipment. Fleet discounts available for multi-unit purchases.",
                "headline": "Upgrade Your Fleet Today",
                "cta": "Request Pricing",
            },
        ],
    },
}

_GENERIC_STUB: dict = {
    "angles": [
        "Speed to lead — first responder wins the deal",
        "Social proof — trusted by hundreds of customers",
        "Low barrier offer — free consultation or quote",
        "Urgency — limited availability or seasonal pricing",
    ],
    "hooks": [
        "Ready to get started? It takes less than 60 seconds.",
        "See why hundreds of customers chose us.",
        "Get a free, no-obligation quote today.",
        "Limited spots available this month — don't wait.",
        "Your competitors are already using this. Are you?",
        "What would solving this problem be worth to you?",
    ],
    "offers": [
        "Free consultation — no strings attached",
        "Get a quote in under 24 hours",
        "Limited-time introductory pricing",
    ],
    "targeting": [
        "Homeowners or business owners in your service area",
        "Lookalike audience based on existing customers",
        "Interest-based targeting matching your service category",
        "Retarget website visitors who started but didn't submit the form",
    ],
    "ads": [
        {
            "primary_text": "Looking for a trusted partner? Get a free consultation and see how we can help. No pressure, no obligation — just honest answers.",
            "headline": "Free Consultation Available",
            "cta": "Book Now",
        },
        {
            "primary_text": "Hundreds of customers trust us to deliver results. See what we can do for you — get a personalized quote in under 24 hours.",
            "headline": "Trusted By Hundreds",
            "cta": "Get Your Quote",
        },
        {
            "primary_text": "Don't wait — our introductory pricing won't last. Take the first step today and see why our customers keep coming back.",
            "headline": "Limited-Time Offer",
            "cta": "Learn More",
        },
    ],
}


def _generate_angles_stub(industry_slug: str) -> list[str]:
    """Generate angles from deterministic stub."""
    return _INDUSTRY_STUBS.get(industry_slug, _GENERIC_STUB)["angles"]


def _generate_hooks_stub(industry_slug: str) -> list[str]:
    """Generate hooks from deterministic stub."""
    return _INDUSTRY_STUBS.get(industry_slug, _GENERIC_STUB)["hooks"]


def _generate_offers_stub(industry_slug: str) -> list[str]:
    """Generate offers from deterministic stub."""
    return _INDUSTRY_STUBS.get(industry_slug, _GENERIC_STUB)["offers"]


def _strategy_stub(org_data: dict) -> dict:
    """Deterministic ad strategy based on industry slug."""
    slug = org_data.get("industry_slug", "generic")
    base = _INDUSTRY_STUBS.get(slug, _GENERIC_STUB)
    return {
        "angles": _generate_angles_stub(slug),
        "hooks": _generate_hooks_stub(slug),
        "offers": _generate_offers_stub(slug),
        "targeting": base["targeting"],
        "ads": base["ads"],
        "mode": "stub",
    }


async def generate_ad_strategy(
    org_data: dict, goal: str, budget: float, notes: str | None = None
) -> dict:
    """
    Generate a full ad campaign strategy.
    org_data should include: industry_name, industry_slug, avg_deal_value,
    close_rate_percent, scoring_config.
    Returns structured JSON with angles, hooks, offers, targeting, ads.
    Never throws.
    """
    api_key = os.getenv("CLAUDE_API_KEY", "")

    if api_key:
        try:
            return await _call_claude_strategy(api_key, org_data, goal, budget, notes)
        except Exception:
            return _strategy_stub(org_data)

    return _strategy_stub(org_data)


async def _call_claude_strategy(
    api_key: str, org_data: dict, goal: str, budget: float, notes: str | None
) -> dict:
    industry_name = org_data.get("industry_name", "general business")
    avg_deal = org_data.get("avg_deal_value", 5000)
    close_rate = org_data.get("close_rate_percent", 10)
    scoring_info = ""
    if org_data.get("scoring_config"):
        scoring_info = f"\nScoring rubric: {json.dumps(org_data['scoring_config'])}"

    notes_section = f"\nAdditional notes from the user: {notes}" if notes else ""

    prompt = (
        f"You are an expert digital advertising strategist for the {industry_name} industry.\n\n"
        f"Business context:\n"
        f"- Average deal value: ${avg_deal:,.0f}\n"
        f"- Close rate: {close_rate}%\n"
        f"- Campaign goal: {goal}\n"
        f"- Monthly ad budget: ${budget:,.0f}\n"
        f"{scoring_info}{notes_section}\n\n"
        "Generate a complete ad campaign strategy as a JSON object with these exact keys:\n"
        "- \"angles\": array of 4-5 strategic angles (short phrases describing the approach)\n"
        "- \"hooks\": array of 6-8 hook lines for ads (attention-grabbing first lines)\n"
        "- \"offers\": array of 3-4 offer suggestions (what to offer the prospect)\n"
        "- \"targeting\": array of 4 targeting suggestions (audience descriptions)\n"
        "- \"ads\": array of 3 complete ad variations, each with:\n"
        "  - \"primary_text\": 2-3 sentences of ad body copy\n"
        "  - \"headline\": short headline (under 10 words)\n"
        "  - \"cta\": call-to-action button text (2-3 words)\n\n"
        "Focus on high-value lead generation. Avoid generic fluff. "
        "Be specific to the industry and deal value.\n\n"
        "Respond with ONLY valid JSON, no other text."
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["content"][0]["text"]
        result = json.loads(text)
        result["mode"] = "claude"
        return result
