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

        print("\nSeed complete!")
        print("  Login: admin@solarprime.com / admin123")
        print("  Funnel slug: solar-prime")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
