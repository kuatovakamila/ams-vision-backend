from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from ..models.permission import Permission
from ..models.user_permission import UserPermission
from ..schemas.permission import (
    PermissionCreate,
    PermissionUpdate,
    UserPermissionCreate,
)


class PermissionRepository:
    async def get(self, db: AsyncSession, permission_id: int) -> Optional[Permission]:
        result = await db.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Permission]:
        result = await db.execute(select(Permission).where(Permission.name == name))
        return result.scalar_one_or_none()

    async def get_by_resource_action(
        self, db: AsyncSession, resource: str, action: str
    ) -> Optional[Permission]:
        result = await db.execute(
            select(Permission).where(
                Permission.resource == resource, Permission.action == action
            )
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        resource: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[Permission]:
        """Return permissions with optional filtering by resource and action."""
        query = select(Permission)
        if resource is not None:
            query = query.where(Permission.resource == resource)
        if action is not None:
            query = query.where(Permission.action == action)
        result = await db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_by_resource(
        self, db: AsyncSession, resource: str
    ) -> List[Permission]:
        result = await db.execute(
            select(Permission).where(Permission.resource == resource)
        )
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: PermissionCreate) -> Permission:
        db_obj = Permission(
            name=obj_in.name,
            description=obj_in.description,
            resource=obj_in.resource,
            action=obj_in.action,
            is_system=obj_in.is_system,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, db_obj: Permission, obj_in: PermissionUpdate
    ) -> Permission:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self, db: AsyncSession, permission_id: int
    ) -> Optional[Permission]:
        permission = await self.get(db, permission_id)
        if permission and not permission.is_system:
            await db.delete(permission)
            await db.commit()
            return permission
        return None

    async def remove(self, db: AsyncSession, id: int) -> Optional[Permission]:
        """Backward-compatible alias for delete used by some API routes."""
        return await self.delete(db, permission_id=id)

    async def get_system_permissions(self, db: AsyncSession) -> List[Permission]:
        """Get all system permissions"""
        result = await db.execute(
            select(Permission).where(Permission.is_system.is_(True))
        )
        return result.scalars().all()


class UserPermissionRepository:
    async def get(
        self, db: AsyncSession, user_permission_id: int
    ) -> Optional[UserPermission]:
        result = await db.execute(
            select(UserPermission)
            .options(
                selectinload(UserPermission.user),
                selectinload(UserPermission.permission),
                selectinload(UserPermission.granter),
            )
            .where(UserPermission.id == user_permission_id)
        )
        return result.scalar_one_or_none()

    async def get_user_permission(
        self, db: AsyncSession, user_id: int, permission_id: int
    ) -> Optional[UserPermission]:
        result = await db.execute(
            select(UserPermission).where(
                UserPermission.user_id == user_id,
                UserPermission.permission_id == permission_id,
                UserPermission.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_user_permissions(
        self, db: AsyncSession, user_id: int, active_only: bool = True
    ) -> List[UserPermission]:
        query = (
            select(UserPermission)
            .options(
                selectinload(UserPermission.permission),
                selectinload(UserPermission.granter),
            )
            .where(UserPermission.user_id == user_id)
        )

        if active_only:
            query = query.where(UserPermission.is_active.is_(True))

        result = await db.execute(query)
        return result.scalars().all()

    async def get_all_user_permissions(
        self, db: AsyncSession, user_id: int
    ) -> List[UserPermission]:
        """Return all (active and inactive) direct permissions for a user."""
        result = await db.execute(
            select(UserPermission)
            .options(
                selectinload(UserPermission.permission),
                selectinload(UserPermission.granter),
            )
            .where(UserPermission.user_id == user_id)
        )
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, obj_in: UserPermissionCreate
    ) -> UserPermission:
        """Create a direct user-permission grant. If an active grant exists, raise, mirroring API behavior."""
        existing = await self.get_user_permission(
            db, obj_in.user_id, obj_in.permission_id
        )
        if existing:
            # Mirror API layer: duplication should be handled before calling create
            return existing

        db_obj = UserPermission(
            user_id=obj_in.user_id,
            permission_id=obj_in.permission_id,
            granted_by=obj_in.granted_by,
            expires_at=obj_in.expires_at,
            is_active=obj_in.is_active if hasattr(obj_in, "is_active") else True,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, id: int) -> Optional[UserPermission]:
        """Soft-revoke a user-permission grant by setting is_active=False."""
        up = await self.get(db, id)
        if not up:
            return None
        up.is_active = False
        await db.commit()
        await db.refresh(up)
        return up

    async def grant_permission(
        self, db: AsyncSession, obj_in: UserPermissionCreate, granted_by_id: int
    ) -> UserPermission:
        # Check if permission already exists and is active
        existing = await self.get_user_permission(
            db, obj_in.user_id, obj_in.permission_id
        )
        if existing:
            # Update existing permission
            existing.is_active = True
            existing.expires_at = obj_in.expires_at
            existing.granted_by = granted_by_id
            await db.commit()
            await db.refresh(existing)
            return existing

        # Create new permission
        db_obj = UserPermission(
            user_id=obj_in.user_id,
            permission_id=obj_in.permission_id,
            granted_by=granted_by_id,
            expires_at=obj_in.expires_at,
            is_active=True,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def revoke_permission(
        self, db: AsyncSession, user_id: int, permission_id: int
    ) -> bool:
        user_permission = await self.get_user_permission(db, user_id, permission_id)
        if user_permission:
            user_permission.is_active = False
            await db.commit()
            return True
        return False

    async def bulk_grant_permissions(
        self,
        db: AsyncSession,
        user_id: int,
        permission_ids: List[int],
        granted_by_id: int,
    ) -> List[UserPermission]:
        """Grant multiple permissions to a user"""
        granted_permissions = []
        for permission_id in permission_ids:
            obj_in = UserPermissionCreate(user_id=user_id, permission_id=permission_id)
            granted = await self.grant_permission(db, obj_in, granted_by_id)
            granted_permissions.append(granted)
        return granted_permissions

    async def bulk_revoke_permissions(
        self, db: AsyncSession, user_id: int, permission_ids: List[int]
    ) -> int:
        """Revoke multiple permissions from a user"""
        revoked_count = 0
        for permission_id in permission_ids:
            if await self.revoke_permission(db, user_id, permission_id):
                revoked_count += 1
        return revoked_count

    async def get_expired_permissions(self, db: AsyncSession) -> List[UserPermission]:
        """Get all expired permissions"""
        from datetime import datetime

        result = await db.execute(
            select(UserPermission).where(
                UserPermission.expires_at.isnot(None),
                UserPermission.expires_at < datetime.utcnow(),
                UserPermission.is_active.is_(True),
            )
        )
        return result.scalars().all()

    async def cleanup_expired_permissions(self, db: AsyncSession) -> int:
        """Deactivate expired permissions"""
        expired_permissions = await self.get_expired_permissions(db)
        count = 0
        for perm in expired_permissions:
            perm.is_active = False
            count += 1

        if count > 0:
            await db.commit()

        return count


permission_repository = PermissionRepository()
user_permission_repository = UserPermissionRepository()
