"""
Seed script: runs migrations and inserts sample data.
Usage: python seed.py
"""

import asyncio
import json
import os
import sys

import asyncpg

# Allow importing from app
sys.path.insert(0, os.path.dirname(__file__))

from app.core.security import hash_password


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/leadforge",
)

# Normalise the URL for asyncpg (strip SQLAlchemy driver prefix if present)
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


FUNNEL_SCHEMA = {
    "slug": "solar-prime",
    "languages": ["en", "es"],
    "steps": [
        {
            "id": "service",
            "title": {"en": "What do you need?", "es": "\u00bfQu\u00e9 necesita?"},
            "fields": [
                {
                    "key": "service",
                    "type": "select",
                    "required": True,
                    "label": {"en": "Service", "es": "Servicio"},
                    "options": [
                        {"value": "solar", "label": {"en": "Solar Installation", "es": "Instalaci\u00f3n Solar"}},
                        {"value": "buy", "label": {"en": "Buy a House", "es": "Comprar Casa"}},
                        {"value": "sell", "label": {"en": "Sell a House", "es": "Vender Casa"}},
                    ],
                }
            ],
        },
        {
            "id": "contact_info",
            "title": {"en": "Your Information", "es": "Su Informaci\u00f3n"},
            "fields": [
                {
                    "key": "zip_code",
                    "type": "text",
                    "required": True,
                    "label": {"en": "Zip Code", "es": "C\u00f3digo Postal"},
                },
                {
                    "key": "name",
                    "type": "text",
                    "required": True,
                    "label": {"en": "Full Name", "es": "Nombre Completo"},
                },
            ],
        },
        {
            "id": "phone_info",
            "title": {"en": "Contact Preferences", "es": "Preferencias de Contacto"},
            "fields": [
                {
                    "key": "phone",
                    "type": "tel",
                    "required": True,
                    "label": {"en": "Phone Number", "es": "N\u00famero de Tel\u00e9fono"},
                },
                {
                    "key": "contact_time",
                    "type": "select",
                    "required": True,
                    "label": {"en": "Preferred Contact Time", "es": "Horario de Contacto Preferido"},
                    "options": [
                        {"value": "morning", "label": {"en": "Morning (9am-12pm)", "es": "Ma\u00f1ana (9am-12pm)"}},
                        {"value": "afternoon", "label": {"en": "Afternoon (12pm-5pm)", "es": "Tarde (12pm-5pm)"}},
                        {"value": "evening", "label": {"en": "Evening (5pm-8pm)", "es": "Noche (5pm-8pm)"}},
                    ],
                },
            ],
        },
    ],
}


INDUSTRY_DATA = [
    {
        "slug": "generic",
        "name": "Generic",
        "description": "Default industry profile for general-purpose lead capture",
        "template": {
            "default_funnel_json": {
                "languages": ["en"],
                "steps": [
                    {
                        "id": "service",
                        "title": {"en": "What service do you need?"},
                        "fields": [
                            {
                                "key": "service",
                                "type": "select",
                                "required": True,
                                "label": {"en": "Service"},
                                "options": [
                                    {"value": "solar", "label": {"en": "Solar Installation"}},
                                    {"value": "roofing", "label": {"en": "Roofing"}},
                                    {"value": "other", "label": {"en": "Other"}},
                                ],
                            }
                        ],
                    },
                    {
                        "id": "contact_info",
                        "title": {"en": "Your Information"},
                        "fields": [
                            {"key": "zip_code", "type": "text", "required": True, "label": {"en": "Zip Code"}},
                            {"key": "name", "type": "text", "required": True, "label": {"en": "Full Name"}},
                        ],
                    },
                    {
                        "id": "phone_info",
                        "title": {"en": "Contact Preferences"},
                        "fields": [
                            {"key": "phone", "type": "tel", "required": True, "label": {"en": "Phone Number"}},
                            {"key": "contact_time", "type": "select", "required": False, "label": {"en": "Best time to call"}, "options": [
                                {"value": "morning", "label": {"en": "Morning"}},
                                {"value": "afternoon", "label": {"en": "Afternoon"}},
                                {"value": "evening", "label": {"en": "Evening"}},
                            ]},
                        ],
                    },
                ],
            },
            "default_sequence_json": {
                "steps": [
                    {"delay_minutes": 0, "message": "Thanks for your request, {{name}}! We'll be in touch shortly."},
                    {"delay_minutes": 1440, "message": "Hi {{name}}, just checking in on your inquiry. Any questions?"},
                    {"delay_minutes": 4320, "message": "Hi {{name}}, we'd love to help — reply to schedule a call!"},
                ],
            },
            "default_scoring_json": {
                "rubric": "Score leads 0-100 based on intent signals, budget indicators, and timeline urgency.",
            },
            "default_avg_deal_value": 5000,
            "default_close_rate_percent": 10,
        },
    },
    {
        "slug": "marine_dealer",
        "name": "Marine Dealer",
        "description": "Boat dealerships and marine sales organizations",
        "template": {
            "default_funnel_json": {
                "languages": ["en"],
                "steps": [
                    {
                        "id": "interest",
                        "title": {"en": "What are you looking for?"},
                        "fields": [
                            {
                                "key": "interested_model",
                                "type": "text",
                                "required": True,
                                "label": {"en": "Boat Model / Type"},
                            },
                            {
                                "key": "financing_interest",
                                "type": "select",
                                "required": True,
                                "label": {"en": "Financing Interest"},
                                "options": [
                                    {"value": "yes", "label": {"en": "Yes, I need financing"}},
                                    {"value": "no", "label": {"en": "No, paying cash"}},
                                    {"value": "unsure", "label": {"en": "Not sure yet"}},
                                ],
                            },
                        ],
                    },
                    {
                        "id": "details",
                        "title": {"en": "Additional Details"},
                        "fields": [
                            {
                                "key": "trade_in",
                                "type": "select",
                                "required": False,
                                "label": {"en": "Do you have a trade-in?"},
                                "options": [
                                    {"value": "yes", "label": {"en": "Yes"}},
                                    {"value": "no", "label": {"en": "No"}},
                                ],
                            },
                            {
                                "key": "timeframe",
                                "type": "select",
                                "required": True,
                                "label": {"en": "Purchase Timeframe"},
                                "options": [
                                    {"value": "immediate", "label": {"en": "Ready now"}},
                                    {"value": "1_month", "label": {"en": "Within 1 month"}},
                                    {"value": "3_months", "label": {"en": "Within 3 months"}},
                                    {"value": "browsing", "label": {"en": "Just browsing"}},
                                ],
                            },
                        ],
                    },
                    {
                        "id": "contact",
                        "title": {"en": "Your Information"},
                        "fields": [
                            {"key": "name", "type": "text", "required": True, "label": {"en": "Full Name"}},
                            {"key": "phone", "type": "tel", "required": True, "label": {"en": "Phone Number"}},
                            {"key": "zip_code", "type": "text", "required": True, "label": {"en": "Zip Code"}},
                        ],
                    },
                ],
            },
            "default_sequence_json": {
                "steps": [
                    {"delay_minutes": 0, "message": "Thanks for your interest, {{name}}! Our marine sales team will be in touch shortly."},
                    {"delay_minutes": 1440, "message": "Hi {{name}}, following up on your boat inquiry. Would you like to schedule a showing?"},
                    {"delay_minutes": 4320, "message": "Hi {{name}}, just checking in — we have great inventory available. Reply to connect!"},
                ],
            },
            "default_scoring_json": {
                "rubric": "Score marine leads 0-100. High scores for: immediate timeframe, financing interest, trade-in (repeat buyer signal). Lower scores for 'just browsing' with no financing interest.",
            },
            "default_avg_deal_value": 12000,
            "default_close_rate_percent": 12,
        },
    },
    {
        "slug": "equipment_dealer",
        "name": "Equipment Dealer",
        "description": "Heavy equipment and machinery dealerships",
        "template": {
            "default_funnel_json": {
                "languages": ["en"],
                "steps": [
                    {
                        "id": "equipment",
                        "title": {"en": "Equipment Needs"},
                        "fields": [
                            {
                                "key": "equipment_type",
                                "type": "text",
                                "required": True,
                                "label": {"en": "Equipment Type / Model"},
                            },
                            {
                                "key": "job_size",
                                "type": "select",
                                "required": True,
                                "label": {"en": "Job Size"},
                                "options": [
                                    {"value": "small", "label": {"en": "Small (residential)"}},
                                    {"value": "medium", "label": {"en": "Medium (commercial)"}},
                                    {"value": "large", "label": {"en": "Large (industrial)"}},
                                ],
                            },
                        ],
                    },
                    {
                        "id": "purchase",
                        "title": {"en": "Purchase Details"},
                        "fields": [
                            {
                                "key": "rental_vs_purchase",
                                "type": "select",
                                "required": True,
                                "label": {"en": "Rental or Purchase?"},
                                "options": [
                                    {"value": "purchase", "label": {"en": "Purchase"}},
                                    {"value": "rental", "label": {"en": "Rental"}},
                                    {"value": "lease", "label": {"en": "Lease"}},
                                ],
                            },
                            {
                                "key": "timeframe",
                                "type": "select",
                                "required": True,
                                "label": {"en": "Timeframe"},
                                "options": [
                                    {"value": "immediate", "label": {"en": "Immediate need"}},
                                    {"value": "1_month", "label": {"en": "Within 1 month"}},
                                    {"value": "3_months", "label": {"en": "Within 3 months"}},
                                    {"value": "planning", "label": {"en": "Just planning"}},
                                ],
                            },
                        ],
                    },
                    {
                        "id": "contact",
                        "title": {"en": "Your Information"},
                        "fields": [
                            {"key": "name", "type": "text", "required": True, "label": {"en": "Full Name"}},
                            {"key": "phone", "type": "tel", "required": True, "label": {"en": "Phone Number"}},
                            {"key": "zip_code", "type": "text", "required": True, "label": {"en": "Zip Code"}},
                        ],
                    },
                ],
            },
            "default_sequence_json": {
                "steps": [
                    {"delay_minutes": 0, "message": "Thanks {{name}}! Our equipment specialist will reach out shortly."},
                    {"delay_minutes": 1440, "message": "Hi {{name}}, following up on your equipment inquiry. Ready to discuss options?"},
                    {"delay_minutes": 4320, "message": "Hi {{name}}, we have equipment available for your needs. Reply to get a quote!"},
                ],
            },
            "default_scoring_json": {
                "rubric": "Score equipment leads 0-100. High scores for: purchase intent (vs rental), immediate timeframe, large job size. Lower scores for planning-stage rental inquiries.",
            },
            "default_avg_deal_value": 45000,
            "default_close_rate_percent": 8,
        },
    },
]

SAMPLE_LEADS = [
    {
        "language": "en",
        "answers": {
            "service": "solar",
            "zip_code": "90210",
            "name": "John Smith",
            "phone": "3105551234",
            "contact_time": "morning",
        },
        "source": {"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "solar-summer"},
    },
    {
        "language": "es",
        "answers": {
            "service": "buy",
            "zip_code": "33101",
            "name": "Maria Garcia",
            "phone": "7865559876",
            "contact_time": "afternoon",
        },
        "source": {"utm_source": "facebook", "utm_medium": "social", "referrer": "https://facebook.com"},
    },
    {
        "language": "en",
        "answers": {
            "service": "sell",
            "zip_code": "10001",
            "name": "Robert Johnson",
            "phone": "2125554321",
            "contact_time": "evening",
        },
        "source": {"utm_source": "organic", "landing_url": "/solar-prime"},
    },
    {
        "language": "en",
        "answers": {
            "service": "solar",
            "zip_code": "60601",
            "name": "Emily Davis",
            "phone": "3125557890",
            "contact_time": "morning",
        },
        "source": {"utm_source": "google", "utm_medium": "organic"},
    },
    {
        "language": "es",
        "answers": {
            "service": "solar",
            "zip_code": "78201",
            "name": "Carlos Rodriguez",
            "phone": "2105556543",
            "contact_time": "afternoon",
        },
        "source": {"utm_source": "referral", "referrer": "https://solarprime.com"},
    },
]


async def main():
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Run migrations
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        for migration_file in sorted(os.listdir(migrations_dir)):
            if migration_file.endswith(".sql"):
                migration_path = os.path.join(migrations_dir, migration_file)
                with open(migration_path) as f:
                    migration_sql = f.read()
                print(f"Running migration: {migration_file}...")
                await conn.execute(migration_sql)
        print("Migrations complete.")

        # Create agency
        print("Creating agency...")
        agency_id = await conn.fetchval(
            """
            INSERT INTO agencies (name)
            VALUES ($1)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            "WaveLaunch Marketing",
        )
        if not agency_id:
            agency_id = await conn.fetchval(
                "SELECT id FROM agencies WHERE name = $1", "WaveLaunch Marketing"
            )
        print(f"Agency created: {agency_id}")

        # Create org
        print("Creating org...")
        org_id = await conn.fetchval(
            """
            INSERT INTO orgs (name, slug, branding, agency_id, display_name, primary_color, logo_url, support_email, avg_deal_value, close_rate_percent)
            VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, agency_id = EXCLUDED.agency_id,
                display_name = EXCLUDED.display_name, primary_color = EXCLUDED.primary_color,
                logo_url = EXCLUDED.logo_url, support_email = EXCLUDED.support_email,
                avg_deal_value = EXCLUDED.avg_deal_value, close_rate_percent = EXCLUDED.close_rate_percent
            RETURNING id
            """,
            "SolarPrime Inc",
            "solarprime",
            json.dumps({"primary_color": "#f59e0b", "logo_url": "/logo.svg"}),
            agency_id,
            "SolarPrime",
            "#f59e0b",
            None,
            "support@solarprime.com",
            5000,   # avg_deal_value
            10,     # close_rate_percent
        )
        print(f"Org created: {org_id}")

        # Create admin user
        print("Creating admin user...")
        password_hash = hash_password("admin123")
        await conn.execute(
            """
            INSERT INTO users (org_id, email, password_hash, role)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (email) DO NOTHING
            """,
            org_id,
            "admin@solarprime.com",
            password_hash,
            "admin",
        )
        print("Admin user created: admin@solarprime.com / admin123")

        # Create funnel
        print("Creating funnel...")
        funnel_id = await conn.fetchval(
            """
            INSERT INTO funnels (org_id, slug, name, schema_json, languages)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            ON CONFLICT (slug) DO UPDATE SET schema_json = EXCLUDED.schema_json
            RETURNING id
            """,
            org_id,
            "solar-prime",
            "Solar Prime Lead Funnel",
            json.dumps(FUNNEL_SCHEMA),
            ["en", "es"],
        )
        print(f"Funnel created: {funnel_id}")

        # Update funnel with automation settings
        print("Updating funnel automation settings...")
        routing_rules = {
            "rules": [
                {
                    "when": {"field": "service", "equals": "solar"},
                    "then": {"tag": "solar", "priority": "high"},
                },
                {
                    "when": {"field": "service", "equals": "buy"},
                    "then": {"tag": "buyer", "priority": "medium"},
                },
                {
                    "when": {"field": "service", "equals": "sell"},
                    "then": {"tag": "seller", "priority": "medium"},
                },
            ]
        }
        await conn.execute(
            """
            UPDATE funnels
            SET routing_rules = $1::jsonb,
                auto_email_enabled = $2,
                auto_sms_enabled = $3,
                auto_call_enabled = $4,
                rep_phone_number = $5,
                working_hours_start = $6,
                working_hours_end = $7,
                sequence_enabled = $8,
                sequence_config = $9::jsonb
            WHERE id = $10
            """,
            json.dumps(routing_rules),
            False,
            False,
            False,
            "+15551234567",
            9,
            19,
            False,
            json.dumps({
                "steps": [
                    {"delay_minutes": 0, "message": "Thanks for your interest in SolarPrime!"},
                    {"delay_minutes": 1440, "message": "Just checking in - still interested?"},
                    {"delay_minutes": 4320, "message": "Last chance to connect with our team!"},
                ]
            }),
            funnel_id,
        )
        print("Funnel automation settings updated.")

        # Create industries and templates
        print("Creating industries and templates...")
        for ind in INDUSTRY_DATA:
            industry_id = await conn.fetchval(
                """
                INSERT INTO industries (slug, name, description)
                VALUES ($1, $2, $3)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
                RETURNING id
                """,
                ind["slug"],
                ind["name"],
                ind["description"],
            )
            tmpl = ind["template"]
            await conn.execute(
                """
                INSERT INTO industry_templates
                    (industry_id, default_funnel_json, default_sequence_json,
                     default_scoring_json, default_avg_deal_value, default_close_rate_percent)
                VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5, $6)
                ON CONFLICT (industry_id) DO UPDATE SET
                    default_funnel_json = EXCLUDED.default_funnel_json,
                    default_sequence_json = EXCLUDED.default_sequence_json,
                    default_scoring_json = EXCLUDED.default_scoring_json,
                    default_avg_deal_value = EXCLUDED.default_avg_deal_value,
                    default_close_rate_percent = EXCLUDED.default_close_rate_percent
                """,
                industry_id,
                json.dumps(tmpl["default_funnel_json"]),
                json.dumps(tmpl["default_sequence_json"]),
                json.dumps(tmpl["default_scoring_json"]),
                tmpl["default_avg_deal_value"],
                tmpl["default_close_rate_percent"],
            )
            print(f"  Industry '{ind['slug']}' ready.")

        # Set demo org to generic industry if not already set
        generic_industry_id = await conn.fetchval(
            "SELECT id FROM industries WHERE slug = 'generic'"
        )
        await conn.execute(
            "UPDATE orgs SET industry_id = $1 WHERE id = $2 AND industry_id IS NULL",
            generic_industry_id,
            org_id,
        )
        print("Industries seeded. Demo org set to 'generic'.")

        # Create sample leads
        print("Creating sample leads...")
        for i, lead in enumerate(SAMPLE_LEADS):
            await conn.execute(
                """
                INSERT INTO leads (org_id, funnel_id, language, answers_json, source_json)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                """,
                org_id,
                funnel_id,
                lead["language"],
                json.dumps(lead["answers"]),
                json.dumps(lead["source"]),
            )
            print(f"  Lead {i + 1} created: {lead['answers']['name']}")

        # Create sample campaign (matches "solar-summer" utm_campaign on seeded lead #1)
        print("Creating sample campaign...")
        await conn.execute(
            """
            INSERT INTO campaigns (org_id, source, campaign_name, utm_campaign, ad_spend)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (org_id, utm_campaign) DO UPDATE SET
                ad_spend = EXCLUDED.ad_spend,
                campaign_name = EXCLUDED.campaign_name,
                source = EXCLUDED.source
            """,
            org_id,
            "google",
            "Summer Solar Push",
            "solar-summer",
            250.00,
        )
        print("  Campaign 'Summer Solar Push' (utm: solar-summer, spend: $250)")

        # Mark lead #1 (John Smith) as won with deal_amount
        print("Updating lead #1 pipeline stage...")
        first_lead_id = await conn.fetchval(
            """SELECT id FROM leads WHERE org_id = $1
               ORDER BY created_at ASC LIMIT 1""",
            org_id,
        )
        if first_lead_id:
            await conn.execute(
                """UPDATE leads
                   SET stage = 'won', deal_amount = 8400, stage_updated_at = NOW()
                   WHERE id = $1""",
                first_lead_id,
            )
            print(f"  Lead 1 ({first_lead_id}) → stage=won, deal_amount=$8,400")

        # Seed engagement plan for first lead (idempotent)
        print("Seeding engagement plan for first lead...")
        if first_lead_id:
            from datetime import datetime, timedelta, timezone as tz
            import uuid

            # Check if plan already exists
            existing_plan = await conn.fetchval(
                "SELECT id FROM engagement_plans WHERE lead_id = $1 AND status = 'active'",
                first_lead_id,
            )
            if not existing_plan:
                plan_id = await conn.fetchval(
                    """
                    INSERT INTO engagement_plans (lead_id, org_id, funnel_id, status)
                    VALUES ($1, $2, $3, 'active')
                    RETURNING id
                    """,
                    first_lead_id,
                    org_id,
                    funnel_id,
                )
                now = datetime.now(tz.utc)
                # step_order, channel, scheduled_for, status, content_json
                seed_steps = [
                    (
                        1, "sms",
                        now - timedelta(minutes=5),
                        "sent",
                        json.dumps({
                            "template_key": "intro_sms_1",
                            "sms_body": "Hi John, thanks for reaching out about solar! We'll be in touch shortly. Reply STOP to opt out.",
                        }),
                    ),
                    (
                        2, "email",
                        now - timedelta(minutes=3),
                        "skipped_missing_config",
                        json.dumps({
                            "template_key": "intro_email_1",
                            "email_subject": "Following up on your solar inquiry",
                            "email_body": "Hi John,\n\nThanks for your interest in solar. Our team has received your request and will reach out soon.\n\nBest regards,\nThe Team",
                        }),
                    ),
                    (
                        3, "sms",
                        now + timedelta(hours=1),
                        "pending",
                        json.dumps({
                            "template_key": "followup_sms_1",
                            "sms_body": "Hi John, just checking in on your solar request. Any questions? Reply here.",
                        }),
                    ),
                    (
                        4, "email",
                        now + timedelta(hours=24),
                        "pending",
                        json.dumps({
                            "template_key": "followup_email_1",
                            "email_subject": "Still interested in solar?",
                            "email_body": "Hi John,\n\nWe noticed you haven't had a chance to connect yet regarding solar. We'd love to help — reply to this email or give us a call.\n\nBest regards,\nThe Team",
                        }),
                    ),
                ]
                step_ids = []
                for step_order, channel, scheduled_for, status, content in seed_steps:
                    executed_at = scheduled_for if status in ("sent", "skipped_missing_config") else None
                    step_id = await conn.fetchval(
                        """
                        INSERT INTO engagement_steps
                            (plan_id, step_order, channel, action_type,
                             scheduled_for, executed_at, status, template_key, generated_content_json)
                        VALUES ($1, $2, $3, 'send', $4, $5, $6, $7, $8)
                        RETURNING id
                        """,
                        str(plan_id),
                        step_order,
                        channel,
                        scheduled_for,
                        executed_at,
                        status,
                        json.loads(content).get("template_key"),
                        content,
                    )
                    step_ids.append((step_order, channel, status, step_id))

                # Log engagement events for completed steps, tied to step IDs
                for step_order, channel, status, step_id in step_ids:
                    if status == "sent":
                        event_type = f"{channel}_sent"
                        content_snip = (
                            "Hi John, thanks for reaching out about solar! We'll be in touch shortly."
                            if channel == "sms" else "Following up on your solar inquiry"
                        )
                    elif status == "skipped_missing_config":
                        event_type = f"{channel}_skipped_missing_config"
                        content_snip = "Following up on your solar inquiry"
                    else:
                        continue
                    await conn.execute(
                        """
                        INSERT INTO engagement_events
                            (lead_id, org_id, channel, event_type, direction, content, metadata_json)
                        VALUES ($1, $2, $3, $4, 'outbound', $5, $6)
                        """,
                        first_lead_id,
                        org_id,
                        channel,
                        event_type,
                        content_snip,
                        json.dumps({
                            "step_id":    str(step_id),
                            "step_order": step_order,
                            "plan_id":    str(plan_id),
                            "status":     status,
                            "seeded":     True,
                        }),
                    )
                # Log plan_created system event
                await conn.execute(
                    """
                    INSERT INTO engagement_events
                        (lead_id, org_id, channel, event_type, direction, content, metadata_json)
                    VALUES ($1, $2, 'system', 'plan_created', 'system', NULL, $3)
                    """,
                    first_lead_id,
                    org_id,
                    json.dumps({"plan_id": str(plan_id), "steps": len(seed_steps), "seeded": True}),
                )
                print(f"  Engagement plan {plan_id} seeded for lead {first_lead_id}")
            else:
                print(f"  Engagement plan already exists for lead {first_lead_id} — skipping")

        # Seed inbound message for first lead (idempotent)
        print("Seeding inbound message for first lead...")
        if first_lead_id:
            existing_inbound = await conn.fetchval(
                "SELECT id FROM inbound_messages WHERE lead_id = $1 LIMIT 1",
                first_lead_id,
            )
            if not existing_inbound:
                from app.services.reply_classifier import classify_reply
                inbound_body = "This is too expensive"
                classification_result = classify_reply(inbound_body)
                inbound_id = await conn.fetchval(
                    """
                    INSERT INTO inbound_messages
                        (lead_id, org_id, channel, message_body, classification, suggested_response, metadata_json)
                    VALUES ($1, $2, 'sms', $3, $4, $5, $6)
                    RETURNING id
                    """,
                    first_lead_id,
                    org_id,
                    inbound_body,
                    classification_result["classification"],
                    classification_result["suggested_response"],
                    json.dumps({"from_number": "+13105551234", "seeded": True}),
                )
                # Log matching engagement event
                await conn.execute(
                    """
                    INSERT INTO engagement_events
                        (lead_id, org_id, channel, event_type, direction, content, metadata_json)
                    VALUES ($1, $2, 'sms', 'sms_reply', 'inbound', $3, $4)
                    """,
                    first_lead_id,
                    org_id,
                    inbound_body,
                    json.dumps({
                        "inbound_message_id": str(inbound_id),
                        "classification": classification_result["classification"],
                        "suggested_response": classification_result["suggested_response"],
                        "from_number": "+13105551234",
                        "seeded": True,
                    }),
                )
                print(f"  Inbound message seeded: '{inbound_body}' → classification={classification_result['classification']}")
            else:
                print(f"  Inbound message already exists for lead {first_lead_id} — skipping")

        # Seed human_needed handoff case for second lead (idempotent)
        print("Seeding human_needed handoff case for second lead...")
        second_lead_id = await conn.fetchval(
            """SELECT id FROM leads WHERE org_id = $1
               ORDER BY created_at ASC LIMIT 1 OFFSET 1""",
            org_id,
        )
        if second_lead_id:
            existing_handoff_plan = await conn.fetchval(
                "SELECT id FROM engagement_plans WHERE lead_id = $1 AND status = 'active'",
                second_lead_id,
            )
            if not existing_handoff_plan:
                from datetime import datetime, timedelta, timezone as tz
                import uuid

                # Create active plan
                handoff_plan_id = await conn.fetchval(
                    """
                    INSERT INTO engagement_plans (lead_id, org_id, funnel_id, status, paused, escalation_reason)
                    VALUES ($1, $2, $3, 'active', true, 'reply_requires_human')
                    RETURNING id
                    """,
                    second_lead_id,
                    org_id,
                    funnel_id,
                )

                now = datetime.now(tz.utc)
                # One sent step + two pending (will be cancelled) steps
                handoff_steps = [
                    (1, "sms", now - timedelta(minutes=10), "sent",
                     json.dumps({"template_key": "intro_sms_1", "sms_body": "Hi Maria, thanks for your interest in solar!"})),
                    (2, "sms", now + timedelta(hours=2), "cancelled",
                     json.dumps({"template_key": "followup_sms_1", "sms_body": "Hi Maria, following up on solar."})),
                    (3, "email", now + timedelta(hours=24), "cancelled",
                     json.dumps({"template_key": "followup_email_1", "email_subject": "Still interested in solar?", "email_body": "Hi Maria, we'd love to help."})),
                ]
                for step_order, channel, scheduled_for, status, content in handoff_steps:
                    executed_at = scheduled_for if status == "sent" else None
                    await conn.execute(
                        """
                        INSERT INTO engagement_steps
                            (plan_id, step_order, channel, action_type,
                             scheduled_for, executed_at, status, template_key, generated_content_json)
                        VALUES ($1, $2, $3, 'send', $4, $5, $6, $7, $8)
                        """,
                        str(handoff_plan_id),
                        step_order,
                        channel,
                        scheduled_for,
                        executed_at,
                        status,
                        json.loads(content).get("template_key"),
                        content,
                    )

                # Create inbound human_needed message
                handoff_inbound_id = await conn.fetchval(
                    """
                    INSERT INTO inbound_messages
                        (lead_id, org_id, channel, message_body, classification, suggested_response, metadata_json)
                    VALUES ($1, $2, 'sms', $3, 'human_needed', $4, $5)
                    RETURNING id
                    """,
                    second_lead_id,
                    org_id,
                    "I have a complex situation, I need to talk to someone directly",
                    "I completely understand — let me connect you with one of our specialists directly. What time works best for a quick call?",
                    json.dumps({"from_number": "+13105559876", "seeded": True}),
                )

                # Mark lead needs_human
                await conn.execute(
                    """
                    UPDATE leads
                    SET needs_human = true,
                        handoff_reason = 'reply_requires_human',
                        handoff_at = now()
                    WHERE id = $1
                    """,
                    second_lead_id,
                )

                # Log sms_reply event
                await conn.execute(
                    """
                    INSERT INTO engagement_events
                        (lead_id, org_id, channel, event_type, direction, content, metadata_json)
                    VALUES ($1, $2, 'sms', 'sms_reply', 'inbound', $3, $4)
                    """,
                    second_lead_id,
                    org_id,
                    "I have a complex situation, I need to talk to someone directly",
                    json.dumps({
                        "inbound_message_id": str(handoff_inbound_id),
                        "classification": "human_needed",
                        "seeded": True,
                    }),
                )

                # Log handoff_required event
                await conn.execute(
                    """
                    INSERT INTO engagement_events
                        (lead_id, org_id, channel, event_type, direction, content, metadata_json)
                    VALUES ($1, $2, 'system', 'handoff_required', 'system', NULL, $3)
                    """,
                    second_lead_id,
                    org_id,
                    json.dumps({
                        "classification": "human_needed",
                        "inbound_message_id": str(handoff_inbound_id),
                        "seeded": True,
                    }),
                )

                print(f"  Human handoff case seeded for lead {second_lead_id} — needs_human=true, steps cancelled")
            else:
                print(f"  Engagement plan already exists for second lead {second_lead_id} — skipping handoff seed")
        else:
            print("  Second lead not found — skipping handoff seed")

        # ── Warder org + website-demo funnel (Basin webhook target) ──────────
        print("Creating Warder org...")
        warder_org_id = await conn.fetchval(
            """
            INSERT INTO orgs (name, slug, branding, agency_id, display_name, avg_deal_value, close_rate_percent)
            VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7)
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            "Warder AI",
            "warder",
            json.dumps({"primary_color": "#1e293b"}),
            agency_id,
            "Warder AI",
            10000,
            15,
        )
        print(f"  Warder org: {warder_org_id}")

        warder_funnel_schema = {
            "slug": "website-demo",
            "languages": ["en"],
            "steps": [
                {
                    "id": "contact",
                    "title": {"en": "Request a Demo"},
                    "fields": [
                        {"key": "name", "type": "text", "required": False, "label": {"en": "Name"}},
                        {"key": "email", "type": "email", "required": False, "label": {"en": "Email"}},
                        {"key": "phone", "type": "tel", "required": False, "label": {"en": "Phone"}},
                        {"key": "company", "type": "text", "required": False, "label": {"en": "Company"}},
                        {"key": "website", "type": "text", "required": False, "label": {"en": "Website"}},
                        {"key": "message", "type": "textarea", "required": False, "label": {"en": "Message"}},
                    ],
                }
            ],
        }

        warder_funnel_id = await conn.fetchval(
            """
            INSERT INTO funnels (org_id, slug, name, schema_json, languages)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            ON CONFLICT (slug) DO UPDATE SET schema_json = EXCLUDED.schema_json, org_id = EXCLUDED.org_id
            RETURNING id
            """,
            warder_org_id,
            "website-demo",
            "Warder Website Demo Request",
            json.dumps(warder_funnel_schema),
            ["en"],
        )

        await conn.execute(
            """
            UPDATE funnels
            SET sequence_enabled = $1, sequence_config = $2::jsonb,
                auto_email_enabled = $3, auto_sms_enabled = $4, auto_call_enabled = $5
            WHERE id = $6
            """,
            False,
            json.dumps({
                "steps": [
                    {"delay_minutes": 0, "message": "Thanks for your demo request, {{name}}! We'll be in touch shortly."},
                    {"delay_minutes": 1440, "message": "Hi {{name}}, following up on your Warder demo request. Any questions?"},
                ]
            }),
            False,
            False,
            False,
            warder_funnel_id,
        )
        print(f"  Warder funnel 'website-demo': {warder_funnel_id}")
        # ─────────────────────────────────────────────────────────────────────

        print("\nSeed complete!")
        print("  Login: admin@solarprime.com / admin123")
        print("  Funnel slug: solar-prime")
        print("  Basin webhook target: POST /public/leads/basin (org=warder, funnel=website-demo)")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
