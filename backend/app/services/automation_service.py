"""
Automation orchestration: processes routing, AI scoring, and notifications for new leads.
"""

import json
import logging
import os

import asyncpg

from app.services.ai_service import generate_ai_summary
from app.services.event_service import log_event
from app.services.notification_service import send_email, send_sms
from app.services.routing_service import apply_routing_rules

logger = logging.getLogger(__name__)


async def process_automation(lead_id: str, pool: asyncpg.Pool):
    """
    Full automation pipeline for a newly submitted lead:
    a) Load lead + funnel from DB
    b) Apply routing rules -> update lead tags/priority
    c) AI scoring -> update ai_score/ai_summary
    d) If funnel.auto_email_enabled -> send_email -> update email_status
    e) If funnel.auto_sms_enabled -> send_sms -> update sms_status
    f) If funnel.auto_call_enabled -> start call -> update call_status
    """
    try:
        async with pool.acquire() as conn:
            # a) Load lead + funnel
            lead = await conn.fetchrow(
                "SELECT * FROM leads WHERE id = $1", lead_id
            )
            if not lead:
                logger.error(f"Automation: lead {lead_id} not found")
                return

            funnel = await conn.fetchrow(
                "SELECT * FROM funnels WHERE id = $1", lead["funnel_id"]
            )
            if not funnel:
                logger.error(f"Automation: funnel {lead['funnel_id']} not found")
                return

            org_id = lead["org_id"]

            answers = (
                json.loads(lead["answers_json"])
                if isinstance(lead["answers_json"], str)
                else lead["answers_json"]
            )
            routing_rules = (
                json.loads(funnel["routing_rules"])
                if isinstance(funnel["routing_rules"], str)
                else funnel["routing_rules"]
            ) if funnel["routing_rules"] else None

            # b) Routing
            tags, priority = apply_routing_rules(routing_rules, answers)
            await conn.execute(
                "UPDATE leads SET tags = $1, priority = $2 WHERE id = $3",
                tags,
                priority,
                lead_id,
            )
            await log_event(conn, org_id, lead_id, "routed", "success",
                            {"tags": tags, "priority": priority})

            # c) AI scoring (falls back to deterministic stub if Claude not configured)
            scoring_mode = "claude" if os.getenv("CLAUDE_API_KEY", "") else "deterministic"
            if scoring_mode == "deterministic":
                logger.info("Claude API not configured — using deterministic scoring for lead %s", lead_id)
            ai_score, ai_summary = await generate_ai_summary(answers)
            await conn.execute(
                "UPDATE leads SET ai_score = $1, ai_summary = $2 WHERE id = $3",
                ai_score,
                ai_summary,
                lead_id,
            )
            await log_event(conn, org_id, lead_id, "ai_scored", "success",
                            {"score": ai_score, "mode": scoring_mode})

            # Build dicts for notification services
            lead_dict = dict(lead)
            lead_dict["answers_json"] = answers
            lead_dict["tags"] = tags
            lead_dict["priority"] = priority
            lead_dict["ai_score"] = ai_score
            lead_dict["ai_summary"] = ai_summary

            funnel_dict = dict(funnel)

            # d) Email notification
            if funnel["auto_email_enabled"]:
                email_status = await send_email(lead_dict, funnel_dict)
                if email_status == "skipped_missing_config":
                    logger.warning("SMTP not configured — skipping email for lead %s", lead_id)
                await conn.execute(
                    "UPDATE leads SET email_status = $1 WHERE id = $2",
                    email_status,
                    lead_id,
                )
                await log_event(conn, org_id, lead_id, "email_sent", email_status)

            # e) SMS notification
            if funnel["auto_sms_enabled"]:
                sms_status = await send_sms(lead_dict, funnel_dict)
                if sms_status == "skipped_missing_config":
                    logger.warning("Twilio not configured — skipping SMS for lead %s", lead_id)
                await conn.execute(
                    "UPDATE leads SET sms_status = $1 WHERE id = $2",
                    sms_status,
                    lead_id,
                )
                await log_event(conn, org_id, lead_id, "sms_sent", sms_status)

            # f) Auto-call (call_service is created by Agent B)
            if funnel["auto_call_enabled"]:
                try:
                    from app.services.call_service import start_rep_call

                    call_status = await start_rep_call(lead_dict, funnel_dict, pool)
                    await conn.execute(
                        "UPDATE leads SET call_status = $1 WHERE id = $2",
                        call_status,
                        lead_id,
                    )
                    await log_event(conn, org_id, lead_id, "call_started", call_status)
                except ImportError:
                    logger.warning("Twilio call_service not available — skipping auto-call for lead %s", lead_id)
                    await log_event(conn, org_id, lead_id, "call_started", "skipped_missing_config")
                except Exception as e:
                    logger.error(f"Auto-call failed: {e}")
                    await conn.execute(
                        "UPDATE leads SET call_status = 'failed' WHERE id = $1",
                        lead_id,
                    )
                    await log_event(conn, org_id, lead_id, "call_started", "failed",
                                    {"error": str(e)})

            # g) Schedule follow-up sequences
            try:
                from app.services.sequence_service import schedule_sequences
                await schedule_sequences(lead_id, funnel_dict, conn)
                if funnel_dict.get("sequence_enabled"):
                    await log_event(conn, org_id, lead_id, "sequence_scheduled", "success")
            except Exception as e:
                logger.error(f"Sequence scheduling failed: {e}")
                await log_event(conn, org_id, lead_id, "sequence_scheduled", "failed",
                                {"error": str(e)})

        # h) Process any due sequences (outside conn block)
        try:
            from app.services.sequence_worker import process_due_sequences
            await process_due_sequences(pool)
        except Exception as e:
            logger.error(f"Sequence processing failed: {e}")

    except Exception as e:
        logger.error(f"Automation failed for lead {lead_id}: {e}")
