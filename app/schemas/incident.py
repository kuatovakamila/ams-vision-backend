from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# Base schemas
class IncidentBase(BaseModel):
    title: str
    description: Optional[str] = None
    incident_type: str
    status: str = "open"
    priority: str = "medium"
    location: Optional[str] = None
    camera_id: Optional[int] = None
    assigned_to: Optional[int] = None


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    incident_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    location: Optional[str] = None
    camera_id: Optional[int] = None
    assigned_to: Optional[int] = None


class IncidentResponse(IncidentBase):
    id: int
    reported_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentType(BaseModel):
    name: str
    description: Optional[str] = None


class IncidentSummary(BaseModel):
    total_incidents: int
    open_incidents: int
    investigating_incidents: int
    resolved_incidents: int
    closed_incidents: int
    incidents_by_type: List[dict]
    incidents_by_priority: List[dict]
