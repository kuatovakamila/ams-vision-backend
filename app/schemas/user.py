from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role_id: Optional[int] = None
    is_active: bool = True
    is_superadmin: bool = False
    tenant_id: Optional[int] = None


class UserCreate(BaseModel):
    """User registration schema - tenant_id and role are NOT allowed for security reasons.
    Tenant is determined from context (subdomain/header/query) or tenant_slug parameter.
    Role is automatically assigned as 'viewer' (lowest privilege) for security."""
    email: EmailStr
    first_name: str
    last_name: str
    password: str
    is_active: bool = True
    # Note: tenant_id, role_id, role, and is_superadmin are NOT allowed in registration


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[int] = None
    # Optional role name input for convenience
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRoleUpdate(BaseModel):
    role_id: int


# Permission management schemas
class UserPermissionGrant(BaseModel):
    user_id: int
    permission_id: int
    expires_at: Optional[datetime] = None


class UserPermissionRevoke(BaseModel):
    user_id: int
    permission_id: int


# Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    tenant_id: Optional[int] = None


class TokenRefresh(BaseModel):
    refresh_token: str


class UserProfile(UserResponse):
    pass
