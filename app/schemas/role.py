from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from .permission import PermissionResponse


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_role_id: Optional[int] = None
    is_system: bool = False


class RoleCreate(RoleBase):
    permission_ids: Optional[List[int]] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_role_id: Optional[int] = None
    is_system: Optional[bool] = None
    permission_ids: Optional[List[int]] = None


class RoleInDB(RoleBase):
    id: int
    level: int
    path: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RoleResponse(RoleInDB):
    permissions: List[PermissionResponse] = []
