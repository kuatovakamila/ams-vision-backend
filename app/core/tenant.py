from typing import Dict, Any, Optional
from contextvars import ContextVar
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Context variables for tenant information
tenant_id_var: ContextVar[Optional[int]] = ContextVar("tenant_id", default=None)
tenant_slug_var: ContextVar[Optional[str]] = ContextVar("tenant_slug", default=None)
tenant_settings_var: ContextVar[Dict[str, Any]] = ContextVar(
    "tenant_settings", default={}
)

logger = logging.getLogger(__name__)


class TenantService:
    """
    Service for managing tenant context.
    This service provides methods for setting and getting tenant information.
    """

    def set_tenant_id(self, tenant_id: int) -> None:
        """Set the current tenant ID in the context"""
        tenant_id_var.set(tenant_id)
        logger.debug(f"Set tenant_id to {tenant_id}")

    def get_tenant_id(self) -> Optional[int]:
        """Get the current tenant ID from the context"""
        return tenant_id_var.get()

    def set_tenant_slug(self, tenant_slug: str) -> None:
        """Set the current tenant slug in the context"""
        tenant_slug_var.set(tenant_slug)
        logger.debug(f"Set tenant_slug to {tenant_slug}")

    def get_tenant_slug(self) -> Optional[str]:
        """Get the current tenant slug from the context"""
        return tenant_slug_var.get()

    def set_tenant_settings(self, settings: Dict[str, Any]) -> None:
        """Set the current tenant settings in the context"""
        tenant_settings_var.set(settings or {})
        logger.debug(f"Set tenant_settings: {settings}")

    def get_tenant_settings(self) -> Dict[str, Any]:
        """Get the current tenant settings from the context"""
        return tenant_settings_var.get()

    def get_tenant_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific tenant setting from the context"""
        settings = self.get_tenant_settings()
        return settings.get(key, default)

    def clear_tenant_context(self) -> None:
        """Clear all tenant context variables"""
        tenant_id_var.set(None)
        tenant_slug_var.set(None)
        tenant_settings_var.set({})
        logger.debug("Cleared tenant context")

    def has_tenant_context(self) -> bool:
        """Check if tenant context is set"""
        return self.get_tenant_id() is not None

    async def get_tenant_by_slug(
        self, db: AsyncSession, slug: str, active_only: bool = True
    ):
        """
        Get tenant by slug from database.
        
        Args:
            db: Database session
            slug: Tenant slug
            active_only: Only return active tenants
            
        Returns:
            Tenant object or None if not found
        """
        from ..models.tenant import Tenant
        
        query = select(Tenant).where(Tenant.slug == slug)
        if active_only:
            query = query.where(Tenant.status == "active")
        
        result = await db.execute(query)
        return result.scalar_one_or_none()


# Create a singleton instance
tenant_service = TenantService()
