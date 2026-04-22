from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .camera_module import CameraModuleResponse
from .camera_feature import CameraFeatureResponse


class TenantModuleAssignment(BaseModel):
    module_code: str = Field(..., description="Module code to assign to tenant")
    enabled: bool = Field(default=True, description="Whether the module is enabled")


class TenantModuleResponse(BaseModel):
    tenant_id: int
    module_code: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    module: Optional[CameraModuleResponse] = None

    model_config = {"from_attributes": True}


class TenantFeatureOverrideCreate(BaseModel):
    feature_code: str = Field(..., description="Feature code to override")
    enabled: bool = Field(..., description="TRUE = force enable, FALSE = force disable")


class TenantFeatureOverrideResponse(BaseModel):
    tenant_id: int
    feature_code: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    feature: Optional[CameraFeatureResponse] = None

    model_config = {"from_attributes": True}


class TenantFeaturesResponse(BaseModel):
    """Computed list of all enabled features for a tenant"""
    tenant_id: int
    features: List[CameraFeatureResponse] = []
    feature_codes: List[str] = []
    modules: List[CameraModuleResponse] = []
    module_codes: List[str] = []


class TenantModulesListResponse(BaseModel):
    """List of all modules assigned to a tenant"""
    tenant_id: int
    modules: List[TenantModuleResponse] = []

