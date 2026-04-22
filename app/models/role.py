from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    DateTime,
    Table,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base
from .base import TenantMixin

# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class Role(Base, TenantMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)

    # Set the tenant relationship
    tenant = relationship("Tenant", back_populates="roles")
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    parent_role_id = Column(
        Integer, ForeignKey("roles.id"), nullable=True
    )  # For hierarchy
    level = Column(Integer, default=0)  # Hierarchy level
    path = Column(String(255), default="")  # Hierarchy path
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    parent_role = relationship("Role", remote_side=[id], back_populates="child_roles")
    child_roles = relationship("Role", back_populates="parent_role")
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    users = relationship("User", back_populates="role_obj")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}', level={self.level})>"
