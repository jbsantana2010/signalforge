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
