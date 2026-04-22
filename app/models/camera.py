from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base
from .base import TenantMixin


class Camera(Base, TenantMixin):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)

    # Set the tenant relationship
    tenant = relationship("Tenant", back_populates="cameras")
    name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    status = Column(String(50), default="active", nullable=False)  # active, inactive
    ip_address = Column(String(15))  # IPv4 address
    stream_url = Column(String(500))
    created_by = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Who created this camera
    assigned_to = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Who manages this camera
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], backref="created_cameras")
    assignee = relationship(
        "User", foreign_keys=[assigned_to], backref="assigned_cameras"
    )

    def __repr__(self):
        return f"<Camera(id={self.id}, name='{self.name}', location='{self.location}', status='{self.status}')>"
