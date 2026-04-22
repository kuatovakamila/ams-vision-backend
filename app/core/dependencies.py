from typing import List, Tuple
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.security import get_current_user
from ..core.permissions import permission_service
from ..models.user import User


class PermissionChecker:
    """Permission checker for FastAPI dependencies"""

    def __init__(self, resource: str, action: str, require_all: bool = True):
        self.resource = resource
        self.action = action
        self.require_all = require_all

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        # Super admin legacy bypass without extra DB calls
        if current_user.role in ("super_admin", "system_admin"):
            return current_user
        if not await permission_service.has_permission(
            db, current_user.id, self.resource, self.action
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {self.resource}:{self.action}",
            )
        return current_user


class MultiPermissionChecker:
    """Check multiple permissions (any or all)"""

    def __init__(self, permissions: List[Tuple[str, str]], require_all: bool = True):
        self.permissions = permissions
        self.require_all = require_all

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        # Super admin legacy bypass
        if current_user.role in ("super_admin", "system_admin"):
            return current_user
        if self.require_all:
            if not await permission_service.has_all_permissions(
                db, current_user.id, self.permissions
            ):
                perms_str = ", ".join([f"{r}:{a}" for r, a in self.permissions])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required all: {perms_str}",
                )
        else:
            if not await permission_service.has_any_permission(
                db, current_user.id, self.permissions
            ):
                perms_str = ", ".join([f"{r}:{a}" for r, a in self.permissions])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required any: {perms_str}",
                )
        return current_user


class ResourceOwnershipChecker:
    """Check resource ownership + permission"""

    def __init__(self, resource: str, action: str, resource_id_param: str = "id"):
        self.resource = resource
        self.action = action
        self.resource_id_param = resource_id_param

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        # First check basic permission
        if not await permission_service.has_permission(
            db, current_user.id, self.resource, self.action
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {self.resource}:{self.action}",
            )
        return current_user


# Role-based dependency shortcuts
RequireRoleCreate = PermissionChecker("roles", "create")
RequireRoleRead = PermissionChecker("roles", "read")
RequireRoleUpdate = PermissionChecker("roles", "update")
RequireRoleDelete = PermissionChecker("roles", "delete")

# Permission-based dependency shortcuts
RequirePermissionView = PermissionChecker("permissions", "view")
RequirePermissionGrant = PermissionChecker("permissions", "grant")
RequirePermissionRevoke = PermissionChecker("permissions", "revoke")

# User management dependency shortcuts
RequireUserCreate = PermissionChecker("users", "create")
RequireUserRead = PermissionChecker("users", "read")
RequireUserUpdate = PermissionChecker("users", "update")
RequireUserDelete = PermissionChecker("users", "delete")
RequireUserManageAll = PermissionChecker("users", "manage_all")

# Camera management dependency shortcuts
RequireCameraCreate = PermissionChecker("cameras", "create")
RequireCameraRead = PermissionChecker("cameras", "read")
RequireCameraUpdate = PermissionChecker("cameras", "update")
RequireCameraDelete = PermissionChecker("cameras", "delete")
RequireCameraViewFeed = PermissionChecker("cameras", "view_feed")
RequireCameraControl = PermissionChecker("cameras", "control")

# Incident management dependency shortcuts
RequireIncidentCreate = PermissionChecker("incidents", "create")
RequireIncidentRead = PermissionChecker("incidents", "read")
RequireIncidentUpdate = PermissionChecker("incidents", "update")
RequireIncidentDelete = PermissionChecker("incidents", "delete")
RequireIncidentAssign = PermissionChecker("incidents", "assign")
RequireIncidentClose = PermissionChecker("incidents", "close")

# File management dependency shortcuts
RequireFileUpload = PermissionChecker("files", "upload")
RequireFileDownload = PermissionChecker("files", "download")
RequireFileView = PermissionChecker("files", "view")
RequireFileDelete = PermissionChecker("files", "delete")

# System administration dependency shortcuts
RequireSystemAdmin = PermissionChecker("system", "admin")
RequireSystemAudit = PermissionChecker("system", "audit")
RequireSystemConfig = PermissionChecker("system", "config")

# Dashboard and analytics dependency shortcuts
RequireDashboardView = PermissionChecker("dashboard", "view")
RequireAnalyticsView = PermissionChecker("analytics", "view")
