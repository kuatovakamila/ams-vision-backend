import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import async_engine
from app.core.security import get_password_hash


async def seed():
    async with AsyncSession(async_engine) as db:
        # Create default tenant
        await db.execute(text("""
            INSERT INTO tenants (name, slug, status)
            VALUES ('Default', 'default', 'active')
            ON CONFLICT (slug) DO NOTHING
        """))
        await db.commit()

        tenant = (await db.execute(text("SELECT id FROM tenants WHERE slug='default'"))).fetchone()
        tenant_id = tenant[0]

        # Create default roles
        for role_name, description in [
            ('admin',    'Full system access'),
            ('operator', 'Operational access'),
            ('viewer',   'Read-only access'),
        ]:
            await db.execute(text("""
                INSERT INTO roles (name, description, tenant_id)
                VALUES (:name, :description, :tenant_id)
                ON CONFLICT DO NOTHING
            """), {"name": role_name, "description": description, "tenant_id": tenant_id})
        await db.commit()

        admin_role = (await db.execute(text(
            "SELECT id FROM roles WHERE name='admin' AND tenant_id=:tid"),
            {"tid": tenant_id}
        )).fetchone()
        admin_role_id = admin_role[0] if admin_role else None

        # Create default users
        users = [
            ("admin@ams.com",    "admin123",    "Admin",    "User",     "admin",    True),
            ("operator@ams.com", "operator123", "Operator", "User",     "operator", False),
            ("viewer@ams.com",   "viewer123",   "Viewer",   "User",     "viewer",   False),
        ]

        for email, password, first, last, role, is_superadmin in users:
            existing = (await db.execute(
                text("SELECT id FROM users WHERE email=:e"), {"e": email}
            )).fetchone()
            if not existing:
                await db.execute(text("""
                    INSERT INTO users
                        (email, password_hash, first_name, last_name, role, role_id,
                         is_active, is_superadmin, tenant_id)
                    VALUES
                        (:email, :pw, :first, :last, :role, :role_id,
                         true, :superadmin, :tenant_id)
                """), {
                    "email": email,
                    "pw": get_password_hash(password),
                    "first": first,
                    "last": last,
                    "role": role,
                    "role_id": admin_role_id if role == "admin" else None,
                    "superadmin": is_superadmin,
                    "tenant_id": tenant_id,
                })

        await db.commit()
        print("Database seeded successfully.")
        print("  admin@ams.local    / admin123")
        print("  operator@ams.local / operator123")
        print("  viewer@ams.local   / viewer123")


if __name__ == "__main__":
    asyncio.run(seed())
