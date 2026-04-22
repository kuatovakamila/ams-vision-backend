from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from ..models.camera_module import CameraModule
from ..models.camera_feature import CameraFeature
from ..models.tenant_camera_module import TenantCameraModule
from ..models.camera_module import camera_module_features
from ..schemas.camera_module import CameraModuleCreate, CameraModuleUpdate


class CameraModuleRepository:
    async def get(self, db: AsyncSession, code: str) -> Optional[CameraModule]:
        """Get a module by code with features loaded"""
        result = await db.execute(
            select(CameraModule)
            .options(selectinload(CameraModule.features))
            .where(CameraModule.code == code)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[CameraModule]:
        """Get multiple modules"""
        result = await db.execute(
            select(CameraModule)
            .options(selectinload(CameraModule.features))
            .offset(skip)
            .limit(limit)
            .order_by(CameraModule.code)
        )
        return result.scalars().all()

    async def get_all(self, db: AsyncSession) -> List[CameraModule]:
        """Get all modules"""
        result = await db.execute(
            select(CameraModule)
            .options(selectinload(CameraModule.features))
            .order_by(CameraModule.code)
        )
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, obj_in: CameraModuleCreate
    ) -> CameraModule:
        """Create a new module with optional features"""
        db_obj = CameraModule(
            code=obj_in.code,
            name=obj_in.name,
            description=obj_in.description,
        )

        # Add features if provided
        if obj_in.feature_codes:
            result = await db.execute(
                select(CameraFeature).where(
                    CameraFeature.code.in_(obj_in.feature_codes)
                )
            )
            features = result.scalars().all()
            db_obj.features = features

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # Reload with features
        return await self.get(db, obj_in.code)

    async def update(
        self, db: AsyncSession, db_obj: CameraModule, obj_in: CameraModuleUpdate
    ) -> CameraModule:
        """Update a module"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return await self.get(db, db_obj.code)

    async def delete(self, db: AsyncSession, code: str) -> Optional[CameraModule]:
        """Delete a module"""
        module = await self.get(db, code)
        if module:
            await db.delete(module)
            await db.commit()
        return module

    async def add_feature(
        self, db: AsyncSession, module_code: str, feature_code: str
    ) -> Optional[CameraModule]:
        """Add a feature to a module"""
        module = await self.get(db, module_code)
        if not module:
            return None

        feature_result = await db.execute(
            select(CameraFeature).where(CameraFeature.code == feature_code)
        )
        feature = feature_result.scalar_one_or_none()
        if not feature:
            return None

        if feature not in module.features:
            module.features.append(feature)
            await db.commit()
            await db.refresh(module)

        return await self.get(db, module_code)

    async def remove_feature(
        self, db: AsyncSession, module_code: str, feature_code: str
    ) -> Optional[CameraModule]:
        """Remove a feature from a module"""
        module = await self.get(db, module_code)
        if not module:
            return None

        module.features = [f for f in module.features if f.code != feature_code]
        await db.commit()
        await db.refresh(module)

        return await self.get(db, module_code)

    async def count_tenants_with_module(
        self, db: AsyncSession, module_code: str
    ) -> int:
        """Count how many tenants have this module assigned"""
        result = await db.execute(
            select(func.count(TenantCameraModule.tenant_id)).where(
                TenantCameraModule.module_code == module_code,
                TenantCameraModule.enabled == True,
            )
        )
        return int(result.scalar() or 0)


camera_module_repository = CameraModuleRepository()
