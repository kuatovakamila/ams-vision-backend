"""Audit logging service for tracking user actions and permission changes."""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from ..models.audit_log import AuditLog
from ..models.user import User


class AuditService:
    """Service for logging user actions and system events."""

    @staticmethod
    async def log_action(
        db: AsyncSession,
        action: str,
        user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """
        Log an action to the audit trail.

        Args:
            db: Database session
            action: Action performed (e.g., "permission_granted", "role_changed")
            user_id: ID of user who performed the action
            target_user_id: ID of user who was affected by the action
            resource_type: Type of resource affected (e.g., "user", "role", "permission")
            resource_id: ID of the affected resource
            details: Additional context as JSON
            request: FastAPI request object for IP and user agent

        Returns:
            Created AuditLog instance
        """
        audit_log = AuditLog(
            user_id=user_id,
            target_user_id=target_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)

        return audit_log

    @staticmethod
    async def log_permission_change(
        db: AsyncSession,
        action: str,
        user: User,
        target_user_id: int,
        permission_name: str,
        granted: bool,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log permission grant/revoke actions."""
        return await AuditService.log_action(
            db=db,
            action=f"permission_{'granted' if granted else 'revoked'}",
            user_id=user.id,
            target_user_id=target_user_id,
            resource_type="permission",
            details={
                "permission_name": permission_name,
                "granted": granted,
                "action": action,
            },
            request=request,
        )

    @staticmethod
    async def log_role_change(
        db: AsyncSession,
        user: User,
        target_user_id: int,
        old_role: Optional[str],
        new_role: str,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log role changes."""
        return await AuditService.log_action(
            db=db,
            action="role_changed",
            user_id=user.id,
            target_user_id=target_user_id,
            resource_type="user",
            resource_id=target_user_id,
            details={"old_role": old_role, "new_role": new_role},
            request=request,
        )

    @staticmethod
    async def log_user_action(
        db: AsyncSession,
        action: str,
        user: User,
        target_user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log general user actions."""
        return await AuditService.log_action(
            db=db,
            action=action,
            user_id=user.id,
            target_user_id=target_user_id,
            resource_type="user",
            resource_id=target_user_id,
            details=details,
            request=request,
        )

    @staticmethod
    async def log_security_event(
        db: AsyncSession,
        action: str,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log security-related events."""
        return await AuditService.log_action(
            db=db,
            action=action,
            user_id=user_id,
            resource_type="security",
            details=details,
            request=request,
        )
