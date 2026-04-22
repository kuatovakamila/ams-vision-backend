from typing import List, Set, Optional
import json
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.camera_feature import CameraFeature
from ..models.camera_module import CameraModule
from ..repositories import tenant_module_repository, camera_feature_repository
from ..core.redis import get_redis


class CameraFeatureService:
    """Service for checking tenant camera features with Redis caching"""

    def __init__(self, cache_ttl: int = 300):  # 5 minutes default TTL
        self.cache_ttl = cache_ttl

    async def _get_from_cache(self, key: str) -> Optional[Set[str]]:
        """Get features from Redis cache"""
        try:
            redis = await get_redis()
            if redis:
                cached_data = await redis.get(key)
                if cached_data:
                    return set(json.loads(cached_data))
        except Exception:
            pass
        return None

    async def _set_cache(self, key: str, features: Set[str]) -> None:
        """Set features in Redis cache"""
        try:
            redis = await get_redis()
            if redis:
                await redis.setex(key, self.cache_ttl, json.dumps(list(features)))
        except Exception:
            pass

    async def _invalidate_cache(self, tenant_id: int) -> None:
        """Invalidate cache for a tenant"""
        try:
            redis = await get_redis()
            if redis:
                keys = [
                    f"tenant_features_{tenant_id}",
                    f"tenant_feature_codes_{tenant_id}",
                ]
                await redis.delete(*keys)
        except Exception:
            pass

    async def has_feature(
        self, db: AsyncSession, tenant_id: int, feature_code: str
    ) -> bool:
        """
        Check if a tenant has a specific feature enabled.
        Logic:
        1. Check feature overrides first (they take precedence)
        2. If no override, check if feature is in any enabled module assigned to tenant
        """
        # Check for feature override first (using repository)
        override = await tenant_module_repository.get_tenant_feature_override(
            db, tenant_id, feature_code
        )
        if override:
            return override.enabled

        # Check if feature is in any enabled module assigned to tenant
        # Get all enabled modules for tenant (using repository)
        tenant_modules = await tenant_module_repository.get_tenant_modules(
            db, tenant_id, enabled_only=True
        )

        # Check if any module has this feature
        for tenant_module in tenant_modules:
            if tenant_module.module:
                for feature in tenant_module.module.features:
                    if feature.code == feature_code:
                        return True

        return False

    async def get_tenant_features(
        self, db: AsyncSession, tenant_id: int
    ) -> List[CameraFeature]:
        """
        Get all enabled features for a tenant.
        Combines features from modules and overrides (overrides take precedence).
        """
        cache_key = f"tenant_features_{tenant_id}"

        # Try cache first
        cached_codes = await self._get_from_cache(cache_key)
        if cached_codes is not None:
            # Fetch features from repository
            if cached_codes:
                return await camera_feature_repository.get_by_codes(
                    db, list(cached_codes)
                )
            return []

        # Get all enabled modules for tenant (using repository)
        tenant_modules = await tenant_module_repository.get_tenant_modules(
            db, tenant_id, enabled_only=True
        )

        # Collect features from modules
        feature_codes_from_modules: Set[str] = set()
        for tenant_module in tenant_modules:
            if tenant_module.module:
                for feature in tenant_module.module.features:
                    feature_codes_from_modules.add(feature.code)

        # Get all overrides for tenant (using repository)
        overrides = await tenant_module_repository.get_tenant_feature_overrides(
            db, tenant_id
        )

        # Apply overrides
        final_feature_codes: Set[str] = feature_codes_from_modules.copy()
        for override in overrides:
            if override.enabled:
                final_feature_codes.add(override.feature_code)
            else:
                final_feature_codes.discard(override.feature_code)

        # Cache the result
        await self._set_cache(cache_key, final_feature_codes)

        # Fetch and return features (using repository)
        if final_feature_codes:
            return await camera_feature_repository.get_by_codes(
                db, list(final_feature_codes)
            )

        return []

    async def get_tenant_feature_codes(
        self, db: AsyncSession, tenant_id: int
    ) -> Set[str]:
        """Get set of feature codes enabled for a tenant"""
        cache_key = f"tenant_feature_codes_{tenant_id}"

        # Try cache first
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        features = await self.get_tenant_features(db, tenant_id)
        feature_codes = {f.code for f in features}

        # Cache the result
        await self._set_cache(cache_key, feature_codes)

        return feature_codes

    async def get_tenant_modules(
        self, db: AsyncSession, tenant_id: int
    ) -> List[CameraModule]:
        """Get all modules assigned to a tenant (enabled and disabled)"""
        tenant_modules = await tenant_module_repository.get_tenant_modules(
            db, tenant_id, enabled_only=False
        )
        return [tm.module for tm in tenant_modules if tm.module]

    async def invalidate_tenant_cache(self, tenant_id: int) -> None:
        """Invalidate cache for a tenant"""
        await self._invalidate_cache(tenant_id)


# Global service instance
camera_feature_service = CameraFeatureService()

