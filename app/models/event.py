from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
from .base import TenantMixin


class Event(Base, TenantMixin):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    # Set the tenant relationship
    tenant = relationship("Tenant", back_populates="events")
    event_type = Column(String(50), nullable=False, index=True)  # entrance, exit, detection, motion, alarm
    location = Column(String(255))
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Person who triggered the event
    
    # Frigate-specific fields
    frigate_event_id = Column(String(100), nullable=True, unique=True, index=True)  # Frigate event ID
    frigate_type = Column(String(20), nullable=True, index=True)  # new, update, end
    object_type = Column(String(50), nullable=True, index=True)  # person, car, dog, etc.
    confidence = Column(Float, nullable=True)  # Detection confidence score (0-1)
    snapshot_url = Column(String(500), nullable=True)  # URL to Frigate snapshot
    clip_url = Column(String(500), nullable=True)  # URL to Frigate clip
    event_metadata = Column(JSONB, nullable=True)  # Additional Frigate event data (zones, regions, etc.)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    frigate_timestamp = Column(DateTime(timezone=True), nullable=True)  # Original Frigate event timestamp

    # Relationships
    camera = relationship("Camera", backref="events")
    user = relationship("User", backref="events")

    def __repr__(self):
        return f"<Event(id={self.id}, type='{self.event_type}', object='{self.object_type}', camera_id={self.camera_id})>"
