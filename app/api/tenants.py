from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.tenant import Tenant
from ..models.user import User
from ..schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantDetailResponse,
)

router = APIRouter()


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new tenant.
    Only superadmin users can create tenants.
    """
    # Check if user has permission to create tenants
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can create tenants",
        )

    # Check if tenant with same slug already exists
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_data.slug))
    existing_tenant = result.scalar_one_or_none()

    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with slug '{tenant_data.slug}' already exists",
        )

    # Create new tenant
    db_tenant = Tenant(
        name=tenant_data.name,
        slug=tenant_data.slug,
        status=tenant_data.status,
        subscription_plan=tenant_data.subscription_plan,
        subscription_expires_at=tenant_data.subscription_expires_at,
        contact_email=tenant_data.contact_email,
        contact_phone=tenant_data.contact_phone,
        settings=tenant_data.settings or {},
    )

    db.add(db_tenant)
    await db.commit()
    await db.refresh(db_tenant)

    return db_tenant


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all tenants.
    Only superadmin users can list all tenants.
    """
    # Check if user has permission to list tenants
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can list tenants",
        )

    # Build query
    query = select(Tenant)

    # Filter by status if provided
    if status:
        query = query.where(Tenant.status == status)

    # Add pagination
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    tenants = result.scalars().all()

    return tenants


@router.get("/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get tenant details by ID.
    Only superadmin users or users belonging to the tenant can view tenant details.
    """
    # Get tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found",
        )

    # Check if user has permission to view tenant
    if (
        not current_user.is_superadmin
        and getattr(current_user, "tenant_id", None) != tenant.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this tenant",
        )

    # Get user count for tenant
    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id)
    )
    user_count = user_count_result.scalar_one()

    # Create response with user count
    tenant_detail = TenantDetailResponse(**tenant.__dict__, user_count=user_count)

    return tenant_detail


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update tenant details.
    Only superadmin users can update tenants.
    """
    # Check if user has permission to update tenants
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can update tenants",
        )

    # Get tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found",
        )

    # Check if slug is being changed and if new slug already exists
    if tenant_data.slug and tenant_data.slug != tenant.slug:
        result = await db.execute(select(Tenant).where(Tenant.slug == tenant_data.slug))
        existing_tenant = result.scalar_one_or_none()

        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant with slug '{tenant_data.slug}' already exists",
            )

    # Update tenant fields
    for field, value in tenant_data.dict(exclude_unset=True).items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a tenant.
    Only superadmin users can delete tenants.
    """
    # Check if user has permission to delete tenants
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can delete tenants",
        )

    # Get tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found",
        )

    # Delete tenant
    await db.delete(tenant)
    await db.commit()

    return None


@router.get("/by-slug/{slug}", response_model=TenantResponse)
async def get_tenant_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    """
    Get tenant details by slug.
    This endpoint is public and can be used for tenant validation.
    """
    # Get tenant
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with slug '{slug}' not found",
        )

    return tenant
