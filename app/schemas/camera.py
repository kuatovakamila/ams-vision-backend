from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# Base schemas
class CameraBase(BaseModel):
    name: str
    location: str
    description: Optional[str] = None
    status: str = "active"
    ip_address: Optional[str] = None
    stream_url: Optional[str] = None


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    ip_address: Optional[str] = None
    stream_url: Optional[str] = None


class CameraResponse(CameraBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CameraStatusUpdate(BaseModel):
    status: str


class CameraStats(BaseModel):
    total_cameras: int
    active_cameras: int
    inactive_cameras: int
