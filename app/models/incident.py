from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
from .base import TenantMixin


class Incident(Base, TenantMixin):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)

    # Set the tenant relationship
    tenant = relationship("Tenant", back_populates="incidents")
    title = Column(String(255), nullable=False)
    description = Column(Text)
    incident_type = Column(String(100), nullable=False, index=True)
    status = Column(
        String(50), default="open", nullable=False
    )  # open, investigating, resolved, closed
    priority = Column(
        String(50), default="medium", nullable=False
    )  # low, medium, high, critical
    location = Column(String(255))
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    camera = relationship("Camera", backref="incidents")
    reporter = relationship(
        "User", foreign_keys=[reported_by], backref="reported_incidents"
    )
    assignee = relationship(
        "User", foreign_keys=[assigned_to], backref="assigned_incidents"
    )

    def __repr__(self):
        return f"<Incident(id={self.id}, title='{self.title}', type='{self.incident_type}', status='{self.status}')>"
