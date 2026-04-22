from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base


class Tenant(Base):
    """
    Tenant model for multi-tenant architecture.
    Each tenant represents a separate organization or company using the system.
    """

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(
        String(100), nullable=False, unique=True, index=True
    )  # Used for routing/identification
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    status = Column(String(50), default="active")  # active, inactive, trial, etc.
    subscription_plan = Column(String(50), nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    settings = Column(JSONB, default={})  # For tenant-specific configurations

    # Relationships
    users = relationship("User", back_populates="tenant")
    cameras = relationship("Camera", back_populates="tenant")
    incidents = relationship("Incident", back_populates="tenant")
    events = relationship("Event", back_populates="tenant")
    files = relationship("File", back_populates="tenant")
    folders = relationship("Folder", back_populates="tenant")
    roles = relationship("Role", back_populates="tenant")
    camera_modules = relationship(
        "TenantCameraModule", back_populates="tenant", cascade="all, delete-orphan"
    )
    feature_overrides = relationship(
        "TenantFeatureOverride", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}', status='{self.status}')>"
