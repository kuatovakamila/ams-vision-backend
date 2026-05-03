import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import async_engine
from app.core.security import get_password_hash


async def seed():
    async with AsyncSession(async_engine) as db:
        # Tenant
        await db.execute(text("""
            INSERT INTO tenants (name, slug, status)
            VALUES ('Default', 'default', 'active')
            ON CONFLICT (slug) DO NOTHING
        """))
        await db.commit()

        tenant_id = (await db.execute(text("SELECT id FROM tenants WHERE slug='default'"))).fetchone()[0]

        # Roles
        for role_name, description in [
            ('admin',    'Full system access'),
            ('operator', 'Operational access'),
            ('viewer',   'Read-only access'),
        ]:
            await db.execute(text("""
                INSERT INTO roles (name, description, is_system, tenant_id)
                VALUES (:name, :description, false, :tenant_id)
                ON CONFLICT DO NOTHING
            """), {"name": role_name, "description": description, "tenant_id": tenant_id})
        await db.commit()

        admin_role_id = (await db.execute(
            text("SELECT id FROM roles WHERE name='admin' AND tenant_id=:tid"), {"tid": tenant_id}
        )).fetchone()
        admin_role_id = admin_role_id[0] if admin_role_id else None

        # Users
        for email, password, first, last, role, is_superadmin in [
            ("admin@ams.com",    "admin123",    "Admin",    "User",     "admin",    True),
            ("operator@ams.com", "operator123", "Operator", "User",     "operator", False),
            ("viewer@ams.com",   "viewer123",   "Viewer",   "User",     "viewer",   False),
        ]:
            existing = (await db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email})).fetchone()
            if not existing:
                await db.execute(text("""
                    INSERT INTO users (email, password_hash, first_name, last_name, role, role_id,
                                       is_active, is_superadmin, tenant_id)
                    VALUES (:email, :pw, :first, :last, :role, :role_id, true, :superadmin, :tenant_id)
                """), {
                    "email": email, "pw": get_password_hash(password),
                    "first": first, "last": last, "role": role,
                    "role_id": admin_role_id if role == "admin" else None,
                    "superadmin": is_superadmin, "tenant_id": tenant_id,
                })
        await db.commit()

        admin_id = (await db.execute(text("SELECT id FROM users WHERE email='admin@ams.com'"))).fetchone()[0]

        # Cameras
        cameras = [
            ("Главный вход",      "Вход",          "active",   "192.168.1.10", "rtsp://192.168.1.10/stream"),
            ("Парковка A",        "Парковка",       "active",   "192.168.1.11", "rtsp://192.168.1.11/stream"),
            ("Серверная комната", "Этаж 2",         "active",   "192.168.1.12", "rtsp://192.168.1.12/stream"),
            ("Склад",             "Склад",          "inactive", "192.168.1.13", "rtsp://192.168.1.13/stream"),
            ("Переговорная",      "Этаж 3",         "active",   "192.168.1.14", "rtsp://192.168.1.14/stream"),
            ("Запасной выход",    "Выход",          "active",   "192.168.1.15", "rtsp://192.168.1.15/stream"),
        ]
        camera_ids = []
        for name, location, status, ip, stream in cameras:
            existing = (await db.execute(text("SELECT id FROM cameras WHERE name=:n AND tenant_id=:tid"),
                                          {"n": name, "tid": tenant_id})).fetchone()
            if not existing:
                await db.execute(text("""
                    INSERT INTO cameras (name, location, description, status, ip_address, stream_url, tenant_id)
                    VALUES (:name, :loc, :desc, :status, :ip, :stream, :tenant_id)
                """), {"name": name, "loc": location, "desc": f"Камера: {name}", "status": status,
                       "ip": ip, "stream": stream, "tenant_id": tenant_id})
        await db.commit()

        cam_rows = (await db.execute(text("SELECT id FROM cameras WHERE tenant_id=:tid"), {"tid": tenant_id})).fetchall()
        camera_ids = [r[0] for r in cam_rows]

        # Incidents
        incidents = [
            ("Несанкционированный доступ", "Попытка входа без пропуска", "unauthorized_access", "open",       "high",     "Главный вход"),
            ("Сбой камеры",                "Камера на складе не отвечает", "equipment_failure",  "investigating","medium",  "Склад"),
            ("Подозрительная активность",  "Неизвестное лицо в зоне доступа", "security_breach", "open",      "critical", "Парковка A"),
            ("Вандализм",                  "Повреждение оборудования",    "vandalism",          "resolved",   "high",     "Серверная комната"),
            ("Пожарная тревога",           "Срабатывание датчика дыма",   "fire",               "closed",     "critical", "Этаж 2"),
            ("Кража",                      "Пропажа оборудования",        "theft",              "investigating","high",    "Склад"),
        ]
        for title, desc, inc_type, status, priority, location in incidents:
            existing = (await db.execute(text("SELECT id FROM incidents WHERE title=:t AND tenant_id=:tid"),
                                          {"t": title, "tid": tenant_id})).fetchone()
            if not existing:
                cam_id = camera_ids[0] if camera_ids else None
                await db.execute(text("""
                    INSERT INTO incidents (title, description, incident_type, status, priority,
                                           location, reported_by, tenant_id)
                    VALUES (:title, :desc, :type, :status, :priority, :loc, :reporter, :tenant_id)
                """), {"title": title, "desc": desc, "type": inc_type, "status": status,
                       "priority": priority, "loc": location, "reporter": admin_id, "tenant_id": tenant_id})
        await db.commit()

        # Events
        events = [
            ("entrance", "Главный вход",      camera_ids[0] if camera_ids else None, admin_id, "person"),
            ("exit",     "Главный вход",      camera_ids[0] if camera_ids else None, admin_id, "person"),
            ("entrance", "Парковка A",        camera_ids[1] if len(camera_ids) > 1 else None, None, "car"),
            ("exit",     "Парковка A",        camera_ids[1] if len(camera_ids) > 1 else None, None, "car"),
            ("entrance", "Серверная комната", camera_ids[2] if len(camera_ids) > 2 else None, admin_id, "person"),
            ("entrance", "Запасной выход",    camera_ids[5] if len(camera_ids) > 5 else None, None, "person"),
            ("exit",     "Серверная комната", camera_ids[2] if len(camera_ids) > 2 else None, admin_id, "person"),
            ("entrance", "Переговорная",      camera_ids[4] if len(camera_ids) > 4 else None, None, "person"),
        ]
        for ev_type, location, cam_id, user_id, obj_type in events:
            existing = (await db.execute(
                text("SELECT id FROM events WHERE event_type=:t AND location=:l AND tenant_id=:tid LIMIT 1"),
                {"t": ev_type, "l": location, "tid": tenant_id}
            )).fetchone()
            if not existing:
                await db.execute(text("""
                    INSERT INTO events (event_type, location, camera_id, user_id, object_type, tenant_id)
                    VALUES (:type, :loc, :cam, :user, :obj, :tenant_id)
                """), {"type": ev_type, "loc": location, "cam": cam_id,
                       "user": user_id, "obj": obj_type, "tenant_id": tenant_id})
        await db.commit()

        # Folders
        folders = ["Отчёты", "Инциденты", "Архив", "Фото"]
        for folder_name in folders:
            existing = (await db.execute(
                text("SELECT id FROM folders WHERE name=:n AND tenant_id=:tid"),
                {"n": folder_name, "tid": tenant_id}
            )).fetchone()
            if not existing:
                await db.execute(text("""
                    INSERT INTO folders (name, description, path, created_by, tenant_id)
                    VALUES (:name, :desc, :path, :creator, :tenant_id)
                """), {"name": folder_name, "desc": f"Папка: {folder_name}",
                       "path": f"/{folder_name}", "creator": admin_id, "tenant_id": tenant_id})
        await db.commit()

        print("✓ Database seeded successfully.")
        print("  Логин: admin@ams.com    / admin123")
        print("  Логин: operator@ams.com / operator123")
        print("  Логин: viewer@ams.com   / viewer123")


if __name__ == "__main__":
    asyncio.run(seed())
