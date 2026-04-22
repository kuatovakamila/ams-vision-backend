from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class TenantFeatureOverride(Base):
    """
    Per-tenant feature overrides to add/remove individual features
    without modifying module assignments.
    Overrides take precedence over module-based features.
    """

    __tablename__ = "tenant_features_override"

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    feature_code = Column(
        String(100),
        ForeignKey("features.code", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    enabled = Column(
        Boolean, nullable=False
    )  # TRUE = force enable, FALSE = force disable
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="feature_overrides")
    feature = relationship("CameraFeature", back_populates="tenant_overrides")

    def __repr__(self):
        return f"<TenantFeatureOverride(tenant_id={self.tenant_id}, feature_code='{self.feature_code}', enabled={self.enabled})>"

