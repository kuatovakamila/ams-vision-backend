from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func
from ..models.role import Role
from ..models.permission import Permission
from ..models.user import User
from ..schemas.role import RoleCreate, RoleUpdate


class RoleRepository:
    async def get(self, db: AsyncSession, role_id: int) -> Optional[Role]:
        result = await db.execute(
            select(Role)
            .options(
                selectinload(Role.permissions),
                selectinload(Role.parent_role),
                selectinload(Role.child_roles),
            )
            .where(Role.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self, db: AsyncSession, name: str, tenant_id: Optional[int] = None
    ) -> Optional[Role]:
        """Get role by name, optionally filtered by tenant_id"""
        query = select(Role).where(Role.name == name)
        if tenant_id is not None:
            query = query.where(Role.tenant_id == tenant_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Role]:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions), selectinload(Role.parent_role))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_hierarchy(
        self, db: AsyncSession, root_role_id: Optional[int] = None
    ) -> List[Role]:
        """Get role hierarchy starting from root or specified role"""
        if root_role_id:
            root_role = await self.get(db, root_role_id)
            if not root_role:
                return []
            return [root_role]
        else:
            # Get all root roles (no parent)
            result = await db.execute(
                select(Role)
                .options(selectinload(Role.permissions), selectinload(Role.child_roles))
                .where(Role.parent_role_id.is_(None))
            )
            return result.scalars().all()

    async def get_user_accessible_roles(
        self, db: AsyncSession, user_role_id: int
    ) -> List[Role]:
        """Get roles that a user can assign (same level or lower in hierarchy)"""
        user_role = await self.get(db, user_role_id)
        if not user_role:
            return []

        # Get all roles at same level or lower
        result = await db.execute(select(Role).where(Role.level >= user_role.level))
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: RoleCreate) -> Role:
        # Calculate level and path based on parent
        level = 0
        path = ""

        if obj_in.parent_role_id:
            parent = await self.get(db, obj_in.parent_role_id)
            if parent:
                level = parent.level + 1
                # Use parent's existing path without duplicating parent id
                path = parent.path if parent.path else str(parent.id)

        # Create role
        db_obj = Role(
            name=obj_in.name,
            description=obj_in.description,
            parent_role_id=obj_in.parent_role_id,
            is_system=obj_in.is_system,
            level=level,
            path=path,
        )

        db.add(db_obj)
        await db.flush()  # Get the ID

        # Update path to include current role ID
        if not path:
            db_obj.path = str(db_obj.id)
        else:
            db_obj.path = f"{path}.{db_obj.id}"

        # Add permissions if provided
        if hasattr(obj_in, "permission_ids") and obj_in.permission_ids:
            result = await db.execute(
                select(Permission).where(Permission.id.in_(obj_in.permission_ids))
            )
            permissions = result.scalars().all()
            db_obj.permissions = permissions

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, db_obj: Role, obj_in: RoleUpdate) -> Role:
        update_data = obj_in.model_dump(exclude_unset=True)

        # Handle permission updates explicitly
        permissions_changed = False
        if "permission_ids" in update_data:
            permission_ids = update_data.pop("permission_ids")
            if permission_ids is not None:
                result = await db.execute(
                    select(Permission).where(Permission.id.in_(permission_ids))
                )
                permissions = result.scalars().all()
                db_obj.permissions = permissions
                permissions_changed = True

        # Handle parent role change (recalculate hierarchy)
        if "parent_role_id" in update_data:
            new_parent_id = update_data["parent_role_id"]
            if new_parent_id != db_obj.parent_role_id:
                if new_parent_id:
                    parent = await self.get(db, new_parent_id)
                    if parent:
                        db_obj.level = parent.level + 1
                        db_obj.path = (
                            f"{parent.path}.{db_obj.id}"
                            if parent.path
                            else f"{parent.id}.{db_obj.id}"
                        )
                else:
                    db_obj.level = 0
                    db_obj.path = str(db_obj.id)

        # Update remaining scalar fields, ignore None values (to avoid setting NOT NULL cols to NULL)
        for field, value in update_data.items():
            if value is None:
                continue
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)

        # Invalidate permission cache if needed
        if permissions_changed:
            try:
                from ..core.permissions import permission_service

                await permission_service.invalidate_role_cache(db_obj.id)
            except Exception:
                pass

        # Return fully loaded role with permissions
        reloaded = await db.execute(
            select(Role)
            .options(
                selectinload(Role.permissions),
                selectinload(Role.parent_role),
                selectinload(Role.child_roles),
            )
            .where(Role.id == db_obj.id)
        )
        return reloaded.scalar_one()

    async def delete(self, db: AsyncSession, role_id: int) -> Optional[Role]:
        role = await self.get(db, role_id)
        if role and not role.is_system:
            # Check if role has users assigned
            if role.users:
                raise ValueError("Cannot delete role with assigned users")

            # Check if role has child roles
            if role.child_roles:
                raise ValueError("Cannot delete role with child roles")

            await db.delete(role)
            await db.commit()
            return role
        return None

    async def remove(self, db: AsyncSession, id: int) -> Optional[Role]:
        """Backward-compatible alias for delete used by some API routes."""
        return await self.delete(db, role_id=id)

    async def count_users_with_role(self, db: AsyncSession, role_id: int) -> int:
        """Count number of users assigned to a role"""
        result = await db.execute(
            select(func.count(User.id)).where(User.role_id == role_id)
        )
        return int(result.scalar() or 0)

    async def can_user_manage_role(
        self, db: AsyncSession, user_role_id: int, target_role_id: int
    ) -> bool:
        """Check if user can manage (edit/delete) a specific role"""
        user_role = await self.get(db, user_role_id)
        target_role = await self.get(db, target_role_id)

        if not user_role or not target_role:
            return False

        # Can manage roles at same level or lower
        return user_role.level <= target_role.level

    async def get_inherited_permissions(
        self, db: AsyncSession, role_id: int
    ) -> List[Permission]:
        """Get all permissions including inherited from parent roles without lazy loads.
        Uses the role.path hierarchy to fetch all ancestor roles and eagerly load permissions.
        """
        # Fetch the path for the role
        path_res = await db.execute(select(Role.path).where(Role.id == role_id))
        path = path_res.scalar_one_or_none()
        if not path:
            return []

        try:
            role_ids = [int(part) for part in path.split(".") if part]
        except ValueError:
            role_ids = [role_id]

        if not role_ids:
            role_ids = [role_id]

        # Eagerly load permissions for all roles in the path
        res = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id.in_(role_ids))
        )
        roles = res.scalars().all()

        # Aggregate unique permissions by ID to avoid duplicates
        perm_by_id = {}
        for r in roles:
            for p in r.permissions:
                perm_by_id[p.id] = p

        return list(perm_by_id.values())

    async def assign_permission(
        self, db: AsyncSession, role_id: int, permission_id: int
    ) -> None:
        """Assign a permission to a role if not already assigned"""
        role = await self.get(db, role_id)
        if not role:
            raise ValueError("Role not found")
        result = await db.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        permission = result.scalar_one_or_none()
        if not permission:
            raise ValueError("Permission not found")

        if permission not in role.permissions:
            role.permissions.append(permission)
            await db.commit()
            # Invalidate caches for users with this role
            try:
                from ..core.permissions import permission_service

                await permission_service.invalidate_role_cache(role_id)
            except Exception:
                pass

    async def remove_permission(
        self, db: AsyncSession, role_id: int, permission_id: int
    ) -> None:
        """Remove a permission from a role if assigned"""
        role = await self.get(db, role_id)
        if not role:
            raise ValueError("Role not found")
        role.permissions = [p for p in role.permissions if p.id != permission_id]
        await db.commit()
        # Invalidate caches for users with this role
        try:
            from ..core.permissions import permission_service

            await permission_service.invalidate_role_cache(role_id)
        except Exception:
            pass


role_repository = RoleRepository()
