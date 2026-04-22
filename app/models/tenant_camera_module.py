from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class TenantCameraModule(Base):
    """
    Which modules are enabled for a specific tenant.
    """

    __tablename__ = "tenant_camera_modules"

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    module_code = Column(
        String(100),
        ForeignKey("camera_modules.code", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="camera_modules")
    module = relationship("CameraModule", back_populates="tenant_assignments")

    def __repr__(self):
        return f"<TenantCameraModule(tenant_id={self.tenant_id}, module_code='{self.module_code}', enabled={self.enabled})>"

