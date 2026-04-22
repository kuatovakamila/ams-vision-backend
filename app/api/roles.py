from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.database import get_db
from ..core.dependencies import (
    RequireRoleCreate,
    RequireRoleRead,
    RequireRoleUpdate,
    RequireRoleDelete,
    RequirePermissionView,
    RequirePermissionGrant,
    RequirePermissionRevoke,
)
from ..repositories.role import role_repository
from ..repositories.permission import permission_repository, user_permission_repository
from ..schemas.role import RoleResponse, RoleCreate, RoleUpdate
from ..schemas.permission import (
    PermissionResponse,
    PermissionCreate,
    PermissionUpdate,
    UserPermissionResponse,
    UserPermissionCreate,
)
from ..schemas.user import UserPermissionGrant
from ..models.user import User

router = APIRouter()


# Role endpoints
@router.post("/roles/", response_model=RoleResponse)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireRoleCreate),
):
    """Create a new role"""
    # Check if role name already exists
    existing_role = await role_repository.get_by_name(db, role_in.name)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Role name already exists"
        )

    # Validate parent role if specified
    if role_in.parent_role_id:
        parent_role = await role_repository.get(db, role_in.parent_role_id)
        if not parent_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent role not found"
            )

        # Check if user can create roles under this parent
        if not await role_repository.can_user_manage_role(
            db, current_user.role_id, role_in.parent_role_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create role under specified parent",
            )

    return await role_repository.create(db, role_in)


@router.get("/roles/", response_model=List[RoleResponse])
async def get_roles(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireRoleRead),
):
    """Get all roles"""
    return await role_repository.get_multi(db, skip=skip, limit=limit)


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireRoleRead),
):
    """Get role by ID"""
    role = await role_repository.get(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireRoleUpdate),
):
    """Update a role"""
    role = await role_repository.get(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    # Check if user can manage this role
    if not await role_repository.can_user_manage_role(db, current_user.role_id, role_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update this role"
        )

    # Check if name change would cause conflict
    if role_in.name and role_in.name != role.name:
        existing_role = await role_repository.get_by_name(db, role_in.name)
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already exists",
            )

    return await role_repository.update(db, db_obj=role, obj_in=role_in)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireRoleDelete),
):
    """Delete a role"""
    role = await role_repository.get(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    # Check if user can manage this role
    if not await role_repository.can_user_manage_role(db, current_user.role_id, role_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this role"
        )

    # Check if role has users
    users_count = await role_repository.count_users_with_role(db, role_id)
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role. {users_count} users are assigned to this role",
        )

    await role_repository.remove(db, id=role_id)
    return {"message": "Role deleted successfully"}


# Permission endpoints
@router.get("/permissions/", response_model=List[PermissionResponse])
async def get_permissions(
    skip: int = 0,
    limit: int = 100,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermissionView),
):
    """Get all permissions"""
    return await permission_repository.get_multi(
        db, skip=skip, limit=limit, resource=resource, action=action
    )


@router.post("/permissions/", response_model=PermissionResponse)
async def create_permission(
    permission_in: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermissionGrant),
):
    """Create a new permission"""
    # Check if permission already exists
    existing_permission = await permission_repository.get_by_resource_action(
        db, permission_in.resource, permission_in.action
    )
    if existing_permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Permission already exists"
        )

    return await permission_repository.create(db, obj_in=permission_in)


@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_in: PermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermissionGrant),
):
    """Update a permission"""
    permission = await permission_repository.get(db, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )

    return await permission_repository.update(db, db_obj=permission, obj_in=permission_in)


@router.delete("/permissions/{permission_id}")
async def delete_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermissionRevoke),
):
    """Delete a permission"""
    permission = await permission_repository.get(db, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )

    # Don't allow deletion of system permissions
    if permission.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system permissions",
        )

    await permission_repository.remove(db, id=permission_id)
    return {"message": "Permission deleted successfully"}


# Role-Permission assignment endpoints
@router.post("/roles/{role_id}/permissions/{permission_id}")
async def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermissionGrant),
):
    """Assign a permission to a role"""
    # Check if role exists
    role = await role_repository.get(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    # Check if permission exists
    permission = await permission_repository.get(db, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )

    # Check if user can manage this role
    if not await role_repository.can_user_manage_role(db, current_user.role_id, role_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign permissions to this role",
        )

    # Assign permission to role
    await role_repository.assign_permission(db, role_id, permission_id)
    return {"message": "Permission assigned to role successfully"}


@router.delete("/roles/{role_id}/permissions/{permission_id}")
async def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermissionRevoke),
):
    """Remove a permission from a role"""
    # Check if role exists
    role = await role_repository.get(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    # Check if user can manage this role
    if not await role_repository.can_user_manage_role(db, current_user.role_id, role_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke permissions from this role",
        )

    await role_repository.remove_permission(db, role_id, permission_id)
    return {"message": "Permission removed from role successfully"}


# User-Permission assignment endpoints
@router.post("/users/{user_id}/permissions", response_model=UserPermissionResponse)
async def grant_user_permission(
    user_id: int,
    permission_grant: UserPermissionGrant,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermissionGrant),
):
    """Grant a permission directly to a user"""
    # Check if target user exists
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if permission exists
    permission = await permission_repository.get(db, permission_grant.permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )

    # Check if already granted
    existing_grant = await user_permission_repository.get_user_permission(
        db, user_id, permission_grant.permission_id
    )
    if existing_grant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission already granted to user",
        )

    # Grant permission to user
    create_obj = UserPermissionCreate(
        user_id=user_id,
        permission_id=permission_grant.permission_id,
        expires_at=permission_grant.expires_at,
        granted_by=current_user.id,
    )
    granted = await user_permission_repository.create(db, obj_in=create_obj)
    return granted


@router.delete("/users/{user_id}/permissions/{permission_id}")
async def revoke_user_permission(
    user_id: int,
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermissionRevoke),
):
    """Revoke a permission from a user"""
    # Check if user permission exists
    user_permission = await user_permission_repository.get_user_permission(
        db, user_id, permission_id
    )
    if not user_permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User permission not found"
        )

    await user_permission_repository.remove(db, id=user_permission.id)
    return {"message": "Permission revoked from user successfully"}


@router.get("/users/{user_id}/permissions", response_model=List[UserPermissionResponse])
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermissionView),
):
    """Get all permissions for a user (direct grants)"""
    return await user_permission_repository.get_all_user_permissions(db, user_id)
