from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.tenant import Tenant
from ..repositories import tenant_module_repository, camera_module_repository, camera_feature_repository
from ..services.camera_feature_service import camera_feature_service
from ..schemas.tenant_module import (
    TenantModuleAssignment,
    TenantModuleResponse,
    TenantFeatureOverrideCreate,
    TenantFeatureOverrideResponse,
    TenantFeaturesResponse,
    TenantModulesListResponse,
)
from ..schemas.camera_module import CameraModuleResponse
from ..schemas.camera_feature import CameraFeatureResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()


@router.get("/{tenant_id}/modules", response_model=TenantModulesListResponse)
async def get_tenant_modules(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all modules assigned to a tenant.
    Only superadmin users or users belonging to the tenant can view tenant modules.
    """
    # Check if user has permission
    if not current_user.is_superadmin and getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this tenant's modules",
        )

    # Verify tenant exists
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found",
        )

    tenant_modules = await tenant_module_repository.get_tenant_modules(db, tenant_id)
    return TenantModulesListResponse(
        tenant_id=tenant_id,
        modules=[
            TenantModuleResponse(
                tenant_id=tm.tenant_id,
                module_code=tm.module_code,
                enabled=tm.enabled,
                created_at=tm.created_at,
                updated_at=tm.updated_at,
                module=CameraModuleResponse(**tm.module.__dict__) if tm.module else None,
            )
            for tm in tenant_modules
        ],
    )


@router.post("/{tenant_id}/modules", response_model=TenantModuleResponse, status_code=status.HTTP_201_CREATED)
async def assign_module_to_tenant(
    tenant_id: int,
    assignment: TenantModuleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Assign a module to a tenant.
    Only superadmin users can assign modules to tenants.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can assign modules to tenants",
        )

    # Verify tenant exists
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found",
        )

    # Verify module exists
    module = await camera_module_repository.get(db, assignment.module_code)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module with code '{assignment.module_code}' not found",
        )

    tenant_module = await tenant_module_repository.assign_module(db, tenant_id, assignment)

    # Invalidate cache
    await camera_feature_service.invalidate_tenant_cache(tenant_id)

    return TenantModuleResponse(
        tenant_id=tenant_module.tenant_id,
        module_code=tenant_module.module_code,
        enabled=tenant_module.enabled,
        created_at=tenant_module.created_at,
        updated_at=tenant_module.updated_at,
        module=CameraModuleResponse(**module.__dict__),
    )


@router.delete("/{tenant_id}/modules/{module_code}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_module_from_tenant(
    tenant_id: int,
    module_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a module assignment from a tenant.
    Only superadmin users can remove modules from tenants.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can remove modules from tenants",
        )

    # Verify tenant exists
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found",
        )

    assignment = await tenant_module_repository.get_tenant_module(db, tenant_id, module_code)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_code}' is not assigned to tenant {tenant_id}",
        )

    await tenant_module_repository.remove_module(db, tenant_id, module_code)

    # Invalidate cache
    await camera_feature_service.invalidate_tenant_cache(tenant_id)

    return None


@router.get("/{tenant_id}/features", response_model=TenantFeaturesResponse)
async def get_tenant_features(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all enabled features for a tenant (computed from modules + overrides).
    Only superadmin users or users belonging to the tenant can view tenant features.
    """
    # Check if user has permission
    if not current_user.is_superadmin and getattr(current_user, "tenant_id", None) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this tenant's features",
        )

    # Verify tenant exists
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found",
        )

    # Get enabled features
    features = await camera_feature_service.get_tenant_features(db, tenant_id)
    feature_codes = {f.code for f in features}

    # Get assigned modules
    tenant_modules = await tenant_module_repository.get_tenant_modules(db, tenant_id)
    modules = [
        CameraModuleResponse(**tm.module.__dict__)
        for tm in tenant_modules
        if tm.module and tm.enabled
    ]
    module_codes = [tm.module_code for tm in tenant_modules if tm.enabled]

    return TenantFeaturesResponse(
        tenant_id=tenant_id,
        features=[CameraFeatureResponse(**f.__dict__) for f in features],
        feature_codes=list(feature_codes),
        modules=modules,
        module_codes=module_codes,
    )


@router.post(
    "/{tenant_id}/features/override",
    response_model=TenantFeatureOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feature_override(
    tenant_id: int,
    override: TenantFeatureOverrideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create or update a feature override for a tenant.
    Only superadmin users can create feature overrides.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can create feature overrides",
        )

    # Verify tenant exists
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found",
        )

    # Verify feature exists
    feature = await camera_feature_repository.get(db, override.feature_code)
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature with code '{override.feature_code}' not found",
        )

    tenant_override = await tenant_module_repository.create_feature_override(
        db, tenant_id, override
    )

    # Invalidate cache
    await camera_feature_service.invalidate_tenant_cache(tenant_id)

    return TenantFeatureOverrideResponse(
        tenant_id=tenant_override.tenant_id,
        feature_code=tenant_override.feature_code,
        enabled=tenant_override.enabled,
        created_at=tenant_override.created_at,
        updated_at=tenant_override.updated_at,
        feature=CameraFeatureResponse(**feature.__dict__),
    )


@router.delete(
    "/{tenant_id}/features/override/{feature_code}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_feature_override(
    tenant_id: int,
    feature_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a feature override from a tenant.
    Only superadmin users can remove feature overrides.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can remove feature overrides",
        )

    # Verify tenant exists
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {tenant_id} not found",
        )

    override = await tenant_module_repository.get_tenant_feature_override(
        db, tenant_id, feature_code
    )
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature override for '{feature_code}' not found for tenant {tenant_id}",
        )

    await tenant_module_repository.remove_feature_override(db, tenant_id, feature_code)

    # Invalidate cache
    await camera_feature_service.invalidate_tenant_cache(tenant_id)

    return None

