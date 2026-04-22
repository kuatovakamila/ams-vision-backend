from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from ..core.database import get_db
from ..core.dependencies import (
    RequireUserCreate,
    RequireUserDelete,
    RequireUserManageAll,
)
from ..models.user import User
from ..schemas.user import UserResponse, UserCreate, UserUpdate, UserRoleUpdate
from .auth import get_current_user
from ..repositories.role import role_repository
from ..core.permissions import permission_service

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
):
    # Use permission-based scope: only users with users:manage_all can list all
    if not await permission_service.has_permission(
        db, current_user.id, "users", "manage_all"
    ):
        return [current_user]

    query = select(User)

    # Apply filters
    if search:
        search_filter = or_(
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if role:
        query = query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())

    result = await db.execute(query)
    users = result.scalars().all()

    return users


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireUserCreate),
):
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create new user
    from ..core.security import get_password_hash

    hashed_password = get_password_hash(user_data.password)

    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=user_data.is_active,
    )

    # Assign role by id or by name
    if user_data.role_id is not None:
        role_obj = await role_repository.get(db, user_data.role_id)
        if not role_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )
        db_user.role_id = role_obj.id
        db_user.role = role_obj.name
    elif getattr(user_data, "role", None):
        role_obj = await role_repository.get_by_name(db, user_data.role)
        if not role_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )
        db_user.role_id = role_obj.id
        db_user.role = role_obj.name

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Allow viewing self. Otherwise require users:manage_all or higher role level than target
    if current_user.id != user_id:
        has_manage_all = await permission_service.has_permission(
            db, current_user.id, "users", "manage_all"
        )
        if not has_manage_all:
            can_manage = await permission_service.can_user_manage_user(
                db, current_user.id, user_id
            )
            if not can_manage:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied. Required: users:manage_all or higher role level",
                )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Allow updating self. To update others require users:manage_all or higher role level
    if current_user.id != user_id:
        has_manage_all = await permission_service.has_permission(
            db, current_user.id, "users", "manage_all"
        )
        if not has_manage_all:
            can_manage = await permission_service.can_user_manage_user(
                db, current_user.id, user_id
            )
            if not can_manage:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied. Required: users:manage_all or higher role level",
                )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    update_data = user_update.dict(exclude_unset=True)
    role_change_requested = ("role" in update_data) or ("role_id" in update_data)

    # Restrict role changes to users:manage_all and disallow changing own role
    if role_change_requested:
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own role",
            )
        if not await permission_service.has_permission(
            db, current_user.id, "users", "manage_all"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Required: users:manage_all",
            )

    # Update user fields
    for field, value in update_data.items():
        if field == "password" and value:
            from ..core.security import get_password_hash

            setattr(user, "password_hash", get_password_hash(value))
        elif field == "role_id":
            role_obj = await role_repository.get(db, value) if value is not None else None
            if value is not None and not role_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
                )
            user.role_id = value
            if role_obj:
                user.role = role_obj.name
        elif field == "role":
            if value is None:
                user.role_id = None
                user.role = "viewer"
            else:
                role_obj = await role_repository.get_by_name(db, value)
                if not role_obj:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
                    )
                user.role_id = role_obj.id
                user.role = role_obj.name
        elif field != "password":
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    # Invalidate permission cache if role changed
    await permission_service.invalidate_user_cache(user_id)

    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireUserDelete),
):
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    await db.delete(user)
    await db.commit()

    return {"message": "User deleted successfully"}


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireUserManageAll),
):
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    role_obj = await role_repository.get(db, role_update.role_id)
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    user.role_id = role_obj.id
    # Keep legacy role string in sync
    user.role = role_obj.name
    await db.commit()
    await db.refresh(user)

    # Invalidate permission cache for this user
    await permission_service.invalidate_user_cache(user_id)

    return user
