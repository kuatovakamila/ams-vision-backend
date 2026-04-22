from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


# Base schema
class TenantBase(BaseModel):
    name: str
    slug: str
    status: str = "active"
    subscription_plan: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator("slug")
    def validate_slug(cls, v):
        if not v.isalnum() and not all(c.isalnum() or c == "-" for c in v):
            raise ValueError(
                "Slug must contain only alphanumeric characters and hyphens"
            )
        return v.lower()


# Create schema
class TenantCreate(TenantBase):
    pass


# Update schema
class TenantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

    @validator("slug")
    def validate_slug(cls, v):
        if v is not None:
            if not v.isalnum() and not all(c.isalnum() or c == "-" for c in v):
                raise ValueError(
                    "Slug must contain only alphanumeric characters and hyphens"
                )
            return v.lower()
        return v


# Response schema
class TenantResponse(TenantBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Detailed response schema with additional information
class TenantDetailResponse(TenantResponse):
    user_count: int = 0
