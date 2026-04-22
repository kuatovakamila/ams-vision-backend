from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CameraFeatureBase(BaseModel):
    code: str = Field(..., description="Feature code (e.g. 'people_count')")
    name: str = Field(..., description="Feature display name")
    description: str = Field(..., description="Feature description")


class CameraFeatureCreate(CameraFeatureBase):
    pass


class CameraFeatureUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CameraFeatureResponse(CameraFeatureBase):
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CameraFeatureDetailResponse(CameraFeatureResponse):
    module_count: int = 0  # Number of modules that include this feature

