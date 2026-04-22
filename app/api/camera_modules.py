from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..repositories import camera_module_repository, camera_feature_repository
from ..schemas.camera_module import (
    CameraModuleResponse,
    CameraModuleCreate,
    CameraModuleUpdate,
    CameraModuleDetailResponse,
    CameraModuleFeatureAssignment,
)
from ..schemas.camera_feature import CameraFeatureResponse

router = APIRouter()


@router.get("/", response_model=List[CameraModuleResponse])
async def list_modules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all camera modules.
    Only superadmin users can list modules.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can list modules",
        )

    modules = await camera_module_repository.get_multi(db, skip=skip, limit=limit)
    return modules


@router.post("/", response_model=CameraModuleDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_module(
    module_data: CameraModuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new camera module.
    Only superadmin users can create modules.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can create modules",
        )

    # Check if module with same code already exists
    existing = await camera_module_repository.get(db, module_data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Module with code '{module_data.code}' already exists",
        )

    # Validate feature codes if provided
    if module_data.feature_codes:
        for feature_code in module_data.feature_codes:
            feature = await camera_feature_repository.get(db, feature_code)
            if not feature:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Feature with code '{feature_code}' not found",
                )

    module = await camera_module_repository.create(db, module_data)

    # Get tenant count
    tenant_count = await camera_module_repository.count_tenants_with_module(
        db, module.code
    )

    return CameraModuleDetailResponse(
        **module.__dict__,
        features=[CameraFeatureResponse(**f.__dict__) for f in module.features],
        feature_count=len(module.features),
        tenant_count=tenant_count,
    )


@router.get("/{module_code}", response_model=CameraModuleDetailResponse)
async def get_module(
    module_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get module details with features.
    Only superadmin users can view module details.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can view module details",
        )

    module = await camera_module_repository.get(db, module_code)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module with code '{module_code}' not found",
        )

    tenant_count = await camera_module_repository.count_tenants_with_module(db, module_code)

    return CameraModuleDetailResponse(
        **module.__dict__,
        features=[CameraFeatureResponse(**f.__dict__) for f in module.features],
        feature_count=len(module.features),
        tenant_count=tenant_count,
    )


@router.put("/{module_code}", response_model=CameraModuleDetailResponse)
async def update_module(
    module_code: str,
    module_update: CameraModuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a camera module.
    Only superadmin users can update modules.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can update modules",
        )

    module = await camera_module_repository.get(db, module_code)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module with code '{module_code}' not found",
        )

    updated_module = await camera_module_repository.update(db, module, module_update)
    tenant_count = await camera_module_repository.count_tenants_with_module(
        db, module_code
    )

    return CameraModuleDetailResponse(
        **updated_module.__dict__,
        features=[
            CameraFeatureResponse(**f.__dict__) for f in updated_module.features
        ],
        feature_count=len(updated_module.features),
        tenant_count=tenant_count,
    )


@router.delete("/{module_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(
    module_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a camera module.
    Only superadmin users can delete modules.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can delete modules",
        )

    module = await camera_module_repository.get(db, module_code)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module with code '{module_code}' not found",
        )

    # Check if any tenants are using this module
    tenant_count = await camera_module_repository.count_tenants_with_module(
        db, module_code
    )
    if tenant_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete module '{module_code}' because {tenant_count} tenant(s) are using it",
        )

    await camera_module_repository.delete(db, module_code)
    return None


@router.get("/{module_code}/features", response_model=List[CameraFeatureResponse])
async def get_module_features(
    module_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all features in a module.
    Only superadmin users can view module features.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can view module features",
        )

    module = await camera_module_repository.get(db, module_code)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module with code '{module_code}' not found",
        )

    return [CameraFeatureResponse(**f.__dict__) for f in module.features]


@router.post("/{module_code}/features", response_model=CameraModuleDetailResponse)
async def add_feature_to_module(
    module_code: str,
    assignment: CameraModuleFeatureAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a feature to a module.
    Only superadmin users can modify module features.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can modify module features",
        )

    module = await camera_module_repository.get(db, module_code)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module with code '{module_code}' not found",
        )

    feature = await camera_feature_repository.get(db, assignment.feature_code)
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature with code '{assignment.feature_code}' not found",
        )

    updated_module = await camera_module_repository.add_feature(
        db, module_code, assignment.feature_code
    )
    tenant_count = await camera_module_repository.count_tenants_with_module(
        db, module_code
    )

    return CameraModuleDetailResponse(
        **updated_module.__dict__,
        features=[CameraFeatureResponse(**f.__dict__) for f in updated_module.features],
        feature_count=len(updated_module.features),
        tenant_count=tenant_count,
    )


@router.delete(
    "/{module_code}/features/{feature_code}", response_model=CameraModuleDetailResponse
)
async def remove_feature_from_module(
    module_code: str,
    feature_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a feature from a module.
    Only superadmin users can modify module features.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin users can modify module features",
        )

    module = await camera_module_repository.get(db, module_code)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module with code '{module_code}' not found",
        )

    updated_module = await camera_module_repository.remove_feature(
        db, module_code, feature_code
    )
    tenant_count = await camera_module_repository.count_tenants_with_module(
        db, module_code
    )

    return CameraModuleDetailResponse(
        **updated_module.__dict__,
        features=[CameraFeatureResponse(**f.__dict__) for f in updated_module.features],
        feature_count=len(updated_module.features),
        tenant_count=tenant_count,
    )

