from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None
    resource: str
    action: str
    is_system: bool = False


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_system: Optional[bool] = None


class PermissionInDB(PermissionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class Permission(PermissionInDB):
    pass


class UserPermissionBase(BaseModel):
    user_id: int
    permission_id: int
    expires_at: Optional[datetime] = None
    is_active: bool = True


class UserPermissionCreate(UserPermissionBase):
    granted_by: Optional[int] = None


class UserPermissionUpdate(BaseModel):
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class UserPermissionInDB(UserPermissionBase):
    id: int
    granted_by: Optional[int] = None
    granted_at: datetime

    class Config:
        from_attributes = True


class UserPermissionResponse(UserPermissionInDB):
    pass


class PermissionResponse(PermissionInDB):
    pass
