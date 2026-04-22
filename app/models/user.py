from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base
from .base import TenantMixin


class User(Base, TenantMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Set the tenant relationship
    tenant = relationship("Tenant", back_populates="users")
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(
        String(50), default="viewer", nullable=False
    )  # Keep for backward compatibility
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)  # New RBAC role
    is_active = Column(Boolean, default=True, nullable=False)
    is_superadmin = Column(
        Boolean, default=False, nullable=False
    )  # Superadmin flag for tenant management
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    role_obj = relationship("Role", back_populates="users")
    # Use direct relationship through UserPermission model instead of secondary table
    direct_permissions = relationship(
        "UserPermission", foreign_keys="UserPermission.user_id", back_populates="user"
    )
    granted_permissions = relationship(
        "UserPermission",
        foreign_keys="UserPermission.granted_by",
        back_populates="granter",
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
