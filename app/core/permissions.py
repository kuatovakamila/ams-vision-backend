from typing import List, Set, Optional
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.user import User
from ..models.role import Role
from ..repositories.role import role_repository
from ..repositories.permission import permission_repository, user_permission_repository
from ..schemas.permission import PermissionCreate
from .redis import get_redis


class PermissionService:
    """Service for managing and checking permissions with Redis caching"""

    def __init__(self, cache_ttl: int = 300):  # 5 minutes default TTL
        self.permission_cache = {}  # Fallback in-memory cache
        self.cache_ttl = cache_ttl

    async def _get_from_cache(self, key: str) -> Optional[Set[str]]:
        """Get permissions from Redis cache or fallback to memory cache"""
        try:
            redis = await get_redis()
            if redis:
                cached_data = await redis.get(key)
                if cached_data:
                    return set(json.loads(cached_data))
        except Exception:
            # Fall back to memory cache
            pass

        return self.permission_cache.get(key)

    async def _set_cache(self, key: str, permissions: Set[str]) -> None:
        """Set permissions in Redis cache and memory cache"""
        try:
            redis = await get_redis()
            if redis:
                await redis.setex(key, self.cache_ttl, json.dumps(list(permissions)))
        except Exception:
            # Fall back to memory cache only
            pass

        # Always update memory cache as fallback
        self.permission_cache[key] = permissions

    async def _invalidate_cache(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern"""
        try:
            redis = await get_redis()
            if redis:
                keys = await redis.keys(pattern)
                if keys:
                    await redis.delete(*keys)
        except Exception:
            pass

        # Clear memory cache entries matching pattern
        keys_to_remove = [
            k for k in self.permission_cache.keys() if pattern.replace("*", "") in k
        ]
        for key in keys_to_remove:
            del self.permission_cache[key]

    async def invalidate_user_cache(self, user_id: int) -> None:
        """Invalidate cache for specific user"""
        await self._invalidate_cache(f"user_permissions_{user_id}")

    async def invalidate_role_cache(self, role_id: int) -> None:
        """Invalidate cache for all users with specific role"""
        await self._invalidate_cache("*")  # For simplicity, clear all user caches

    async def get_user_all_permissions(
        self, db: AsyncSession, user_id: int
    ) -> Set[str]:
        """Get all permissions for a user (role + individual permissions) with caching"""
        cache_key = f"user_permissions_{user_id}"

        # Try to get from cache first
        cached_permissions = await self._get_from_cache(cache_key)
        if cached_permissions is not None:
            return cached_permissions

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return set()

        permissions = set()

        # Get role-based permissions
        if user.role_id:
            role_permissions = await role_repository.get_inherited_permissions(
                db, user.role_id
            )
            permissions.update([f"{p.resource}:{p.action}" for p in role_permissions])

        # Get individual user permissions
        user_permissions = await user_permission_repository.get_user_permissions(
            db, user_id, active_only=True
        )
        permissions.update(
            [
                f"{up.permission.resource}:{up.permission.action}"
                for up in user_permissions
            ]
        )

        # Cache the result
        await self._set_cache(cache_key, permissions)

        return permissions

    async def has_permission(
        self, db: AsyncSession, user_id: int, resource: str, action: str
    ) -> bool:
        """Check if user has specific permission"""
        # Super admin override by role name without triggering lazy loads
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()
        if user:
            if user.role in ("super_admin", "system_admin"):
                return True
            if user.role_id:
                role_name_res = await db.execute(
                    select(Role.name).where(Role.id == user.role_id)
                )
                role_name = role_name_res.scalar_one_or_none()
                if role_name in ("super_admin", "system_admin"):
                    return True

        permissions = await self.get_user_all_permissions(db, user_id)
        required_permission = f"{resource}:{action}"

        # Check for exact permission
        if required_permission in permissions:
            return True

        # Check for wildcard permissions
        if (
            f"{resource}:*" in permissions
            or f"*:{action}" in permissions
            or "*:*" in permissions
        ):
            return True

        return False

    async def has_any_permission(
        self, db: AsyncSession, user_id: int, permissions: List[tuple]
    ) -> bool:
        """Check if user has any of the specified permissions"""
        for resource, action in permissions:
            if await self.has_permission(db, user_id, resource, action):
                return True
        return False

    async def has_all_permissions(
        self, db: AsyncSession, user_id: int, permissions: List[tuple]
    ) -> bool:
        """Check if user has all specified permissions"""
        for resource, action in permissions:
            if not await self.has_permission(db, user_id, resource, action):
                return False
        return True

    async def can_access_resource(
        self, db: AsyncSession, user_id: int, resource: str
    ) -> bool:
        """Check if user can access any actions on a resource"""
        permissions = await self.get_user_all_permissions(db, user_id)

        for permission in permissions:
            if permission.startswith(f"{resource}:") or permission in [
                "*:*",
                f"{resource}:*",
            ]:
                return True

        return False

    async def get_user_accessible_resources(
        self, db: AsyncSession, user_id: int
    ) -> Set[str]:
        """Get all resources user has access to"""
        permissions = await self.get_user_all_permissions(db, user_id)
        resources = set()

        for permission in permissions:
            if permission == "*:*":
                # User has access to all resources
                all_permissions = await permission_repository.get_multi(db)
                resources.update([p.resource for p in all_permissions])
                break
            else:
                resource, _ = permission.split(":", 1)
                if resource != "*":
                    resources.add(resource)

        return resources

    async def get_user_actions_for_resource(
        self, db: AsyncSession, user_id: int, resource: str
    ) -> Set[str]:
        """Get all actions user can perform on a resource"""
        permissions = await self.get_user_all_permissions(db, user_id)
        actions = set()

        for permission in permissions:
            if permission == "*:*":
                # User can perform all actions
                resource_permissions = await permission_repository.get_by_resource(
                    db, resource
                )
                actions.update([p.action for p in resource_permissions])
                break
            elif permission == f"{resource}:*":
                # User can perform all actions on this resource
                resource_permissions = await permission_repository.get_by_resource(
                    db, resource
                )
                actions.update([p.action for p in resource_permissions])
            elif permission.startswith(f"{resource}:"):
                _, action = permission.split(":", 1)
                actions.add(action)

        return actions

    def clear_user_cache(self, user_id: int):
        """Clear permission cache for a specific user"""
        cache_key = f"user_permissions_{user_id}"
        if cache_key in self.permission_cache:
            del self.permission_cache[cache_key]

    def clear_all_cache(self):
        """Clear all permission cache"""
        self.permission_cache.clear()

    async def can_user_manage_user(
        self, db: AsyncSession, manager_user_id: int, target_user_id: int
    ) -> bool:
        """Check if a user can manage another user (based on role hierarchy)"""
        from sqlalchemy import select

        manager_result = await db.execute(
            select(User).where(User.id == manager_user_id)
        )
        manager = manager_result.scalar_one_or_none()

        target_result = await db.execute(select(User).where(User.id == target_user_id))
        target = target_result.scalar_one_or_none()

        if not manager or not target:
            return False

        # Admin can manage anyone
        if await self.has_permission(db, manager_user_id, "users", "manage_all"):
            return True

        # Users can't manage themselves through this function
        if manager_user_id == target_user_id:
            return False

        # Check role hierarchy
        if manager.role_id and target.role_id:
            manager_role = await role_repository.get(db, manager.role_id)
            target_role = await role_repository.get(db, target.role_id)

            if manager_role and target_role:
                # Can manage users with lower role level
                return manager_role.level < target_role.level

        return False

    async def get_manageable_users(
        self, db: AsyncSession, manager_user_id: int
    ) -> List[User]:
        """Get all users that a manager can manage"""
        if await self.has_permission(db, manager_user_id, "users", "manage_all"):
            # Admin can manage all users except themselves
            result = await db.execute(select(User).where(User.id != manager_user_id))
            return result.scalars().all()

        manager_result = await db.execute(
            select(User).where(User.id == manager_user_id)
        )
        manager = manager_result.scalar_one_or_none()
        if not manager or not manager.role_id:
            return []

        manager_role = await role_repository.get(db, manager.role_id)
        if not manager_role:
            return []

        # Get users with roles at lower levels
        result = await db.execute(
            select(User)
            .join(Role)
            .where(Role.level > manager_role.level, User.id != manager_user_id)
        )
        return result.scalars().all()

    async def initialize_default_permissions(self, db: AsyncSession):
        """Initialize default system permissions"""
        default_permissions = [
            # User management
            ("users", "create", "Create new users"),
            ("users", "read", "View user information"),
            ("users", "update", "Update user information"),
            ("users", "delete", "Delete users"),
            ("users", "manage_all", "Manage all users regardless of hierarchy"),
            # Camera management
            ("cameras", "create", "Create new cameras"),
            ("cameras", "read", "View camera information"),
            ("cameras", "update", "Update camera settings"),
            ("cameras", "delete", "Delete cameras"),
            ("cameras", "view_feed", "View camera feed"),
            ("cameras", "control", "Control camera (PTZ, etc.)"),
            # Incident management
            ("incidents", "create", "Create new incidents"),
            ("incidents", "read", "View incident information"),
            ("incidents", "update", "Update incident details"),
            ("incidents", "delete", "Delete incidents"),
            ("incidents", "assign", "Assign incidents to users"),
            ("incidents", "close", "Close/resolve incidents"),
            # File management
            ("files", "upload", "Upload files"),
            ("files", "download", "Download files"),
            ("files", "delete", "Delete files"),
            ("files", "view", "View file information"),
            # Role and permission management
            ("roles", "create", "Create new roles"),
            ("roles", "read", "View role information"),
            ("roles", "update", "Update role settings"),
            ("roles", "delete", "Delete roles"),
            ("permissions", "grant", "Grant permissions to users"),
            ("permissions", "revoke", "Revoke permissions from users"),
            ("permissions", "view", "View permission information"),
            # System administration
            ("system", "admin", "System administration access"),
            ("system", "audit", "View audit logs"),
            ("system", "config", "System configuration"),
            # Dashboard and analytics
            ("dashboard", "view", "View dashboard"),
            ("analytics", "view", "View analytics and reports"),
        ]

        created_permissions = []
        for resource, action, description in default_permissions:
            existing = await permission_repository.get_by_resource_action(
                db, resource, action
            )
            if not existing:
                permission_data = {
                    "name": f"{resource.title()} {action.replace('_', ' ').title()}",
                    "description": description,
                    "resource": resource,
                    "action": action,
                    "is_system": True,
                }
                permission = await permission_repository.create(
                    db, PermissionCreate(**permission_data)
                )
                created_permissions.append(permission)

        return created_permissions


# Global permission service instance
permission_service = PermissionService()
