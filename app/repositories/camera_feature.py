from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from ..models.camera_feature import CameraFeature
from ..models.camera_module import camera_module_features
from ..schemas.camera_feature import CameraFeatureCreate, CameraFeatureUpdate


class CameraFeatureRepository:
    async def get(self, db: AsyncSession, code: str) -> Optional[CameraFeature]:
        """Get a feature by code"""
        result = await db.execute(
            select(CameraFeature)
            .options(selectinload(CameraFeature.modules))
            .where(CameraFeature.code == code)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[CameraFeature]:
        """Get multiple features"""
        result = await db.execute(
            select(CameraFeature)
            .options(selectinload(CameraFeature.modules))
            .offset(skip)
            .limit(limit)
            .order_by(CameraFeature.code)
        )
        return result.scalars().all()

    async def get_all(self, db: AsyncSession) -> List[CameraFeature]:
        """Get all features"""
        result = await db.execute(
            select(CameraFeature)
            .options(selectinload(CameraFeature.modules))
            .order_by(CameraFeature.code)
        )
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, obj_in: CameraFeatureCreate
    ) -> CameraFeature:
        """Create a new feature"""
        db_obj = CameraFeature(
            code=obj_in.code,
            name=obj_in.name,
            description=obj_in.description,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, db_obj: CameraFeature, obj_in: CameraFeatureUpdate
    ) -> CameraFeature:
        """Update a feature"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, code: str) -> Optional[CameraFeature]:
        """Delete a feature"""
        feature = await self.get(db, code)
        if feature:
            await db.delete(feature)
            await db.commit()
        return feature

    async def count_modules_with_feature(
        self, db: AsyncSession, feature_code: str
    ) -> int:
        """Count how many modules include this feature"""
        result = await db.execute(
            select(func.count(camera_module_features.c.module_code)).where(
                camera_module_features.c.feature_code == feature_code
            )
        )
        return int(result.scalar() or 0)

    async def get_by_codes(
        self, db: AsyncSession, feature_codes: List[str]
    ) -> List[CameraFeature]:
        """Get features by their codes"""
        if not feature_codes:
            return []
        result = await db.execute(
            select(CameraFeature)
            .options(selectinload(CameraFeature.modules))
            .where(CameraFeature.code.in_(feature_codes))
        )
        return result.scalars().all()


camera_feature_repository = CameraFeatureRepository()

