from typing import Optional, List, Callable, Dict, Any
from fastapi import Request, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import re

from .database import get_db
from .tenant import tenant_service
from ..models.tenant import Tenant


class TenantMiddleware:
    """
    Middleware for handling tenant context in requests.
    This middleware extracts tenant information from the request and sets it in the context.
    """

    def __init__(
        self,
        app,
        exclude_paths: Optional[List[str]] = None,
        tenant_header: str = "X-Tenant",
        tenant_path_param: str = "tenant",
        tenant_query_param: str = "tenant",
        use_subdomain: bool = True,
        subdomain_pattern: str = r"^(?P<tenant>[a-zA-Z0-9-]+)\.",
    ):
        """
        Initialize the tenant middleware.

        Args:
            app: The FastAPI application
            exclude_paths: List of path prefixes to exclude from tenant validation
            tenant_header: The header name for tenant identification
            tenant_path_param: The path parameter name for tenant identification
            tenant_query_param: The query parameter name for tenant identification
            use_subdomain: Whether to extract tenant from subdomain
            subdomain_pattern: Regex pattern for extracting tenant from subdomain
        """
        self.app = app
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        ]
        self.tenant_header = tenant_header
        self.tenant_path_param = tenant_path_param
        self.tenant_query_param = tenant_query_param
        self.use_subdomain = use_subdomain
        self.subdomain_pattern = re.compile(subdomain_pattern)

    async def __call__(
        self, scope: Dict[str, Any], receive: Callable, send: Callable
    ) -> None:
        """
        Process the request and set tenant context.

        Args:
            scope: The ASGI scope
            receive: The ASGI receive function
            send: The ASGI send function
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create a request object
        request = Request(scope=scope, receive=receive)

        # Skip tenant validation for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # Get DB session
        try:
            db = next(get_db())
        except Exception:
            # If DB is not available, continue without tenant validation
            await self.app(scope, receive, send)
            return

        # Extract tenant information
        tenant_slug = await self._extract_tenant(request)

        if tenant_slug:
            # Validate tenant and set context
            try:
                await self._set_tenant_context(db, tenant_slug)
            except HTTPException as e:
                # Handle tenant validation error
                response = Response(
                    content={"detail": e.detail},
                    status_code=e.status_code,
                    media_type="application/json",
                )
                await response(scope, receive, send)
                return

        # Continue with the request
        await self.app(scope, receive, send)

        # Clear tenant context after request
        tenant_service.clear_tenant_context()

    async def _extract_tenant(self, request: Request) -> Optional[str]:
        """
        Extract tenant slug from the request.

        Args:
            request: The FastAPI request object

        Returns:
            The tenant slug if found, None otherwise
        """
        # Try to get tenant from header
        tenant_slug = request.headers.get(self.tenant_header)
        if tenant_slug:
            return tenant_slug

        # Try to get tenant from path parameter
        try:
            tenant_slug = request.path_params.get(self.tenant_path_param)
            if tenant_slug:
                return tenant_slug
        except Exception:
            pass

        # Try to get tenant from query parameter
        try:
            tenant_slug = request.query_params.get(self.tenant_query_param)
            if tenant_slug:
                return tenant_slug
        except Exception:
            pass

        # Try to get tenant from subdomain
        if self.use_subdomain:
            host = request.headers.get("host", "")
            match = self.subdomain_pattern.match(host)
            if match:
                tenant_slug = match.group("tenant")
                if tenant_slug:
                    return tenant_slug

        return None

    async def _set_tenant_context(self, db: AsyncSession, tenant_slug: str) -> None:
        """
        Validate tenant and set tenant context.

        Args:
            db: The database session
            tenant_slug: The tenant slug

        Raises:
            HTTPException: If tenant is not found or inactive
        """
        # Get tenant from database
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug, Tenant.status == "active")
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_slug}' not found or inactive",
            )

        # Set tenant context
        tenant_service.set_tenant_id(tenant.id)
        tenant_service.set_tenant_slug(tenant.slug)
        tenant_service.set_tenant_settings(tenant.settings)
