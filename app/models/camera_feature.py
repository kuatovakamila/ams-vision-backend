from sqlalchemy import Column, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class CameraFeature(Base):
    """
    Atomic AI features that the system supports.
    Examples: people_count, heatmap, fire_alert, helmet_detection, etc.
    """

    __tablename__ = "features"

    code = Column(String(100), primary_key=True, index=True)  # e.g. 'people_count'
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    modules = relationship(
        "CameraModule",
        secondary="camera_module_features",
        back_populates="features",
    )
    tenant_overrides = relationship(
        "TenantFeatureOverride", back_populates="feature", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<CameraFeature(code='{self.code}', name='{self.name}')>"

