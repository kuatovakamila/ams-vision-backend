from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class FrigateEventBase(BaseModel):
    """Base schema for Frigate webhook events"""
    type: str = Field(..., description="Event type: new, update, or end")
    id: str = Field(..., description="Frigate event ID")
    camera: str = Field(..., description="Camera name in Frigate")
    frame_time: float = Field(..., description="Frame timestamp")
    before: Optional[Dict[str, Any]] = Field(None, description="Previous event data")
    after: Dict[str, Any] = Field(..., description="Current event data")


class FrigateDetection(BaseModel):
    """Frigate detection object"""
    id: str
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    box: List[float] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    area: float = Field(..., description="Detection area")
    ratio: float = Field(..., description="Aspect ratio")
    region: List[float] = Field(..., description="Region coordinates")
    type: str = Field(..., description="Object type: person, car, dog, etc.")
    label: str = Field(..., description="Object label")
    sub_label: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    stationary: Optional[bool] = None
    motionless_count: Optional[int] = None
    position_changes: Optional[int] = None


class FrigateEventAfter(BaseModel):
    """Frigate event 'after' data structure"""
    id: str
    camera: str
    frame_time: float
    snapshot: Optional[Dict[str, Any]] = None
    thumbnail: Optional[Dict[str, Any]] = None
    has_snapshot: bool = False
    has_clip: bool = False
    retained: bool = False
    plus_id: Optional[str] = None
    start_time: float
    end_time: Optional[float] = None
    score: Optional[float] = None
    false_positive: bool = False
    zones: Optional[List[str]] = None
    region: Optional[List[float]] = None
    box: Optional[List[float]] = None
    area: Optional[float] = None
    ratio: Optional[float] = None
    top_score: Optional[float] = None
    top_attr: Optional[str] = None
    sub_label: Optional[str] = None
    current_zones: Optional[List[str]] = None
    entered_zones: Optional[List[str]] = None
    has_entered_zone: Optional[bool] = None
    stationary: Optional[bool] = None
    motionless_count: Optional[int] = None
    position_changes: Optional[int] = None
    attributes: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    type: Optional[str] = None


class FrigateWebhookPayload(BaseModel):
    """Complete Frigate webhook payload"""
    type: str = Field(..., description="Event type: new, update, or end")
    id: str = Field(..., description="Frigate event ID")
    camera: str = Field(..., description="Camera name in Frigate")
    frame_time: float = Field(..., description="Frame timestamp")
    before: Optional[FrigateEventAfter] = None
    after: FrigateEventAfter = Field(..., description="Current event data")


class FrigateEventCreate(BaseModel):
    """Schema for creating an event from Frigate webhook"""
    frigate_event_id: str
    frigate_type: str  # new, update, end
    camera_name: str
    object_type: Optional[str] = None
    confidence: Optional[float] = None
    snapshot_url: Optional[str] = None
    clip_url: Optional[str] = None
    frigate_timestamp: Optional[datetime] = None
    event_metadata: Optional[Dict[str, Any]] = None
    event_type: str = "detection"  # detection, motion, alarm, etc.


class FrigateEventResponse(BaseModel):
    """Response schema for Frigate event processing"""
    success: bool
    event_id: Optional[int] = None
    message: str
    camera_id: Optional[int] = None
    tenant_id: Optional[int] = None

