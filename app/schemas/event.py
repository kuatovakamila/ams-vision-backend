from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# Base schemas
class EventBase(BaseModel):
    event_type: str
    location: Optional[str] = None
    camera_id: Optional[int] = None
    user_id: Optional[int] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    event_type: Optional[str] = None
    location: Optional[str] = None
    camera_id: Optional[int] = None
    user_id: Optional[int] = None


class EventResponse(EventBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventType(BaseModel):
    name: str
    description: Optional[str] = None


class EventSummary(BaseModel):
    total_events: int
    entrance_events: int
    exit_events: int
    events_by_type: List[dict]
