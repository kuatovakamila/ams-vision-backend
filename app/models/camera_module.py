from sqlalchemy import Column, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base

# Association table for many-to-many relationship between modules and features
camera_module_features = Table(
    "camera_module_features",
    Base.metadata,
    Column(
        "module_code",
        String(100),
        ForeignKey("camera_modules.code", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "feature_code",
        String(100),
        ForeignKey("features.code", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class CameraModule(Base):
    """
    Business/vertical modules that are presets of features.
    Examples: hotel, cafe, oil_gas, client_acme (custom)
    """

    __tablename__ = "camera_modules"

    code = Column(String(100), primary_key=True, index=True)  # e.g. 'hotel', 'cafe'
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    features = relationship(
        "CameraFeature",
        secondary=camera_module_features,
        back_populates="modules",
    )
    tenant_assignments = relationship(
        "TenantCameraModule",
        back_populates="module",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<CameraModule(code='{self.code}', name='{self.name}')>"

