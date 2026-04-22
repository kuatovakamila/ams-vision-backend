from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(
        String(100), unique=True, nullable=False, index=True
    )  # e.g., "cameras:read"
    resource = Column(String(50), nullable=False, index=True)  # e.g., "cameras"
    action = Column(
        String(50), nullable=False, index=True
    )  # e.g., "read", "write", "delete"
    description = Column(Text)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    roles = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )
    # Don't use secondary table relationship due to multiple FKs - use direct relationship instead

    def __repr__(self):
        return f"<Permission(id={self.id}, name='{self.name}', resource='{self.resource}', action='{self.action}')>"
