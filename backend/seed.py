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

        # Create org
        print("Creating org...")
        org_id = await conn.fetchval(
            """
            INSERT INTO orgs (name, slug, branding)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            "SolarPrime Inc",
            "solarprime",
            json.dumps({"primary_color": "#f59e0b", "logo_url": "/logo.svg"}),
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

        print("\nSeed complete!")
        print("  Login: admin@solarprime.com / admin123")
        print("  Funnel slug: solar-prime")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
