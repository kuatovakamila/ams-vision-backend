from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..models.tenant_camera_module import TenantCameraModule
from ..models.tenant_feature_override import TenantFeatureOverride
from ..models.camera_module import CameraModule
from ..models.camera_feature import CameraFeature
from ..schemas.tenant_module import (
    TenantModuleAssignment,
    TenantFeatureOverrideCreate,
)


class TenantModuleRepository:
    async def get_tenant_modules(
        self, db: AsyncSession, tenant_id: int, enabled_only: bool = False
    ) -> List[TenantCameraModule]:
        """Get all modules assigned to a tenant"""
        query = select(TenantCameraModule).options(
            selectinload(TenantCameraModule.module).selectinload(CameraModule.features)
        ).where(TenantCameraModule.tenant_id == tenant_id)
        
        if enabled_only:
            query = query.where(TenantCameraModule.enabled == True)
        
        result = await db.execute(query)
        return result.scalars().all()

    async def get_tenant_module(
        self, db: AsyncSession, tenant_id: int, module_code: str
    ) -> Optional[TenantCameraModule]:
        """Get a specific tenant-module assignment"""
        result = await db.execute(
            select(TenantCameraModule)
            .options(selectinload(TenantCameraModule.module))
            .where(
                TenantCameraModule.tenant_id == tenant_id,
                TenantCameraModule.module_code == module_code,
            )
        )
        return result.scalar_one_or_none()

    async def assign_module(
        self, db: AsyncSession, tenant_id: int, assignment: TenantModuleAssignment
    ) -> TenantCameraModule:
        """Assign a module to a tenant"""
        # Check if assignment already exists
        existing = await self.get_tenant_module(db, tenant_id, assignment.module_code)
        if existing:
            existing.enabled = assignment.enabled
            await db.commit()
            await db.refresh(existing)
            return existing

        # Create new assignment
        db_obj = TenantCameraModule(
            tenant_id=tenant_id,
            module_code=assignment.module_code,
            enabled=assignment.enabled,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove_module(
        self, db: AsyncSession, tenant_id: int, module_code: str
    ) -> Optional[TenantCameraModule]:
        """Remove a module assignment from a tenant"""
        assignment = await self.get_tenant_module(db, tenant_id, module_code)
        if assignment:
            await db.delete(assignment)
            await db.commit()
        return assignment

    async def get_tenant_feature_overrides(
        self, db: AsyncSession, tenant_id: int
    ) -> List[TenantFeatureOverride]:
        """Get all feature overrides for a tenant"""
        result = await db.execute(
            select(TenantFeatureOverride)
            .options(selectinload(TenantFeatureOverride.feature))
            .where(TenantFeatureOverride.tenant_id == tenant_id)
        )
        return result.scalars().all()

    async def get_tenant_feature_override(
        self, db: AsyncSession, tenant_id: int, feature_code: str
    ) -> Optional[TenantFeatureOverride]:
        """Get a specific feature override"""
        result = await db.execute(
            select(TenantFeatureOverride)
            .options(selectinload(TenantFeatureOverride.feature))
            .where(
                TenantFeatureOverride.tenant_id == tenant_id,
                TenantFeatureOverride.feature_code == feature_code,
            )
        )
        return result.scalar_one_or_none()

    async def create_feature_override(
        self, db: AsyncSession, tenant_id: int, override: TenantFeatureOverrideCreate
    ) -> TenantFeatureOverride:
        """Create or update a feature override"""
        existing = await self.get_tenant_feature_override(
            db, tenant_id, override.feature_code
        )
        if existing:
            existing.enabled = override.enabled
            await db.commit()
            await db.refresh(existing)
            return existing

        db_obj = TenantFeatureOverride(
            tenant_id=tenant_id,
            feature_code=override.feature_code,
            enabled=override.enabled,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove_feature_override(
        self, db: AsyncSession, tenant_id: int, feature_code: str
    ) -> Optional[TenantFeatureOverride]:
        """Remove a feature override"""
        override = await self.get_tenant_feature_override(db, tenant_id, feature_code)
        if override:
            await db.delete(override)
            await db.commit()
        return override


tenant_module_repository = TenantModuleRepository()

