from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .camera_feature import CameraFeatureResponse


class CameraModuleBase(BaseModel):
    code: str = Field(..., description="Module code (e.g. 'hotel', 'cafe')")
    name: str = Field(..., description="Module display name")
    description: str = Field(..., description="Module description")


class CameraModuleCreate(CameraModuleBase):
    feature_codes: Optional[List[str]] = Field(
        default=[], description="List of feature codes to include in this module"
    )


class CameraModuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CameraModuleResponse(CameraModuleBase):
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CameraModuleDetailResponse(CameraModuleResponse):
    features: List[CameraFeatureResponse] = []
    feature_count: int = 0
    tenant_count: int = 0  # Number of tenants using this module


class CameraModuleFeatureAssignment(BaseModel):
    feature_code: str = Field(..., description="Feature code to add to module")


class CameraModuleFeatureRemoval(BaseModel):
    feature_code: str = Field(..., description="Feature code to remove from module")

