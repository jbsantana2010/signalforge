"""Lead intelligence service — computes close probability and signals on read."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


# Stage base weights for close probability heuristic v1
_STAGE_WEIGHTS: dict[str, int] = {
    "new": 10,
    "contacted": 25,
    "qualified": 50,
    "proposal": 70,
    "won": 100,
    "lost": 0,
}

# Median days-in-stage thresholds (beyond these, staleness penalty kicks in)
_STAGE_STALE_DAYS: dict[str, float] = {
    "new": 2,
    "contacted": 5,
    "qualified": 7,
    "proposal": 10,
}


@dataclass
class LeadIntelligence:
    close_probability: int  # 0–100
    days_in_stage: float | None
    is_stale: bool
    stage_leak_warning: bool
    stage_leak_message: str | None


def compute_lead_intelligence(
    stage: str,
    ai_score: int | None,
    deal_amount: float | None,
    stage_updated_at: datetime | None,
    last_contacted_at: datetime | None,
    created_at: datetime | None,
) -> LeadIntelligence:
    """Compute live intelligence signals for a single lead.

    Pure function — no DB, no IO. Designed for request-scoped use.
    """
    now = datetime.now(timezone.utc)

    # --- 1. Base probability from stage ---
    base = _STAGE_WEIGHTS.get(stage, 10)

    # Terminal stages: return immediately
    if stage in ("won", "lost"):
        return LeadIntelligence(
            close_probability=base,
            days_in_stage=None,
            is_stale=False,
            stage_leak_warning=False,
            stage_leak_message=None,
        )

    # --- 2. Days in current stage ---
    ref_time = stage_updated_at or created_at
    if ref_time:
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)
        days_in_stage = round((now - ref_time).total_seconds() / 86400.0, 1)
    else:
        days_in_stage = None

    # --- 3. AI score adjustment (+/- up to 15 points) ---
    ai_adj = 0
    if ai_score is not None:
        if ai_score >= 70:
            ai_adj = 15
        elif ai_score >= 50:
            ai_adj = 5
        elif ai_score < 30:
            ai_adj = -10

    # --- 4. Deal amount influence (+5 if set on active stage) ---
    deal_adj = 5 if deal_amount and deal_amount > 0 else 0

    # --- 5. Staleness penalty ---
    stale_threshold = _STAGE_STALE_DAYS.get(stage)
    is_stale = False
    stale_penalty = 0
    if stale_threshold and days_in_stage is not None and days_in_stage > stale_threshold:
        is_stale = True
        excess_days = days_in_stage - stale_threshold
        stale_penalty = min(int(excess_days * 3), 25)  # max -25

    # --- 6. No-contact penalty ---
    contact_penalty = 0
    if stage != "new" and last_contacted_at is None:
        contact_penalty = 10
    elif last_contacted_at:
        if last_contacted_at.tzinfo is None:
            last_contacted_at = last_contacted_at.replace(tzinfo=timezone.utc)
        days_since_contact = (now - last_contacted_at).total_seconds() / 86400.0
        if days_since_contact > 7:
            contact_penalty = 10

    # --- 7. Stage leak warning ---
    stage_leak_warning = False
    stage_leak_message = None
    if is_stale and days_in_stage is not None and stale_threshold:
        ratio = days_in_stage / stale_threshold
        if ratio >= 3:
            stage_leak_warning = True
            stage_leak_message = f"Lead stuck in '{stage}' for {days_in_stage:.0f} days — high risk of loss"
        elif ratio >= 2:
            stage_leak_warning = True
            stage_leak_message = f"Lead in '{stage}' for {days_in_stage:.0f} days — needs attention"

    # --- Final computation ---
    probability = base + ai_adj + deal_adj - stale_penalty - contact_penalty
    probability = max(0, min(100, probability))

    return LeadIntelligence(
        close_probability=probability,
        days_in_stage=days_in_stage,
        is_stale=is_stale,
        stage_leak_warning=stage_leak_warning,
        stage_leak_message=stage_leak_message,
    )


def intelligence_to_dict(intel: LeadIntelligence) -> dict:
    return asdict(intel)
