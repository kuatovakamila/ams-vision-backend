from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.database import get_db
from ..core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_token,
    get_current_user,
    needs_rehash,
)
from ..models.user import User
from ..schemas.user import (
    UserLogin,
    Token,
    TokenRefresh,
    UserCreate,
    UserResponse,
    UserUpdate,
    UserProfile,
)

router = APIRouter()


# Authentication endpoints
@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    # Find user by email
    result = await db.execute(select(User).where(User.email == user_credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # Migrate bcrypt password to Argon2 if needed (automatic migration on login)
    if needs_rehash(user.password_hash):
        user.password_hash = get_password_hash(user_credentials.password)
        await db.commit()

    # Get tenant_id if available
    tenant_id = getattr(user, "tenant_id", None)

    # Create tokens with tenant context
    access_token = create_access_token(data={"sub": str(user.id)}, tenant_id=tenant_id)
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, tenant_id=tenant_id
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        tenant_id=tenant_id,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    payload = verify_token(token_data.refresh_token, "refresh")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Get tenant_id from token if available
    tenant_id = payload.get("tenant_id")

    # Build query
    query = select(User).where(User.id == int(user_id))

    # Add tenant filter if tenant_id is available
    if tenant_id is not None and hasattr(User, "tenant_id"):
        query = query.where(User.tenant_id == tenant_id)

    # Execute query
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens with tenant context
    access_token = create_access_token(data={"sub": str(user.id)}, tenant_id=tenant_id)
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id)}, tenant_id=tenant_id
    )

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        tenant_id=tenant_id,
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # In a more complex implementation, you would invalidate the token in Redis
    return {"message": "Successfully logged out"}


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    tenant_slug: Optional[str] = None,
):
    # Import here to avoid circular imports
    try:
        from ..core.tenant import tenant_service
    except ImportError:
        tenant_service = None

    from ..repositories.role import role_repository
    from ..models.tenant import Tenant

    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Security: Tenant must be determined from context, NOT from user input
    # This prevents users from registering themselves to any tenant
    tenant_id = None
    
    # Priority 1: tenant_id from context (set by middleware from subdomain/header/query)
    if tenant_service:
        tenant_id = tenant_service.get_tenant_id()

    # Priority 2: tenant_id from tenant_slug parameter (for explicit tenant selection)
    if tenant_id is None and tenant_slug:
        if not tenant_service:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant service not available",
            )
        tenant = await tenant_service.get_tenant_by_slug(db, tenant_slug, active_only=True)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with slug '{tenant_slug}' not found or inactive",
            )
        tenant_id = tenant.id
    
    # Require tenant_id for registration (multi-tenant system)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant is required for registration. Provide tenant via subdomain, header (X-Tenant), query parameter (?tenant=slug), or tenant_slug parameter.",
        )

    # Security: Users cannot choose their own role during registration
    # Always assign the default "viewer" role (lowest privilege)
    # Only admins can assign roles when creating users via /api/v1/users/ endpoint
    role_name = "viewer"  # Default role for all registrations
    role_id = None
    
    # Find the "viewer" role for the tenant
    role_obj = await role_repository.get_by_name(db, role_name, tenant_id=tenant_id)
    if role_obj:
        role_id = role_obj.id
        role_name = role_obj.name
    # If viewer role doesn't exist, role_id will be None (handled by database default)

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=role_name,
        role_id=role_id,
        is_active=user_data.is_active,
        is_superadmin=False,  # Always False for registration
        tenant_id=tenant_id,
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Update user fields
    for field, value in user_update.dict(exclude_unset=True).items():
        if field == "password" and value:
            setattr(current_user, "password_hash", get_password_hash(value))
        elif field != "password":
            setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)

    return current_user
