from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# Base schemas
class FolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Folder name")
    description: Optional[str] = Field(None, description="Folder description")
    parent_id: Optional[int] = Field(None, description="Parent folder ID")


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Folder name"
    )
    description: Optional[str] = Field(None, description="Folder description")
    parent_id: Optional[int] = Field(None, description="Parent folder ID")


class FolderResponse(FolderBase):
    id: int
    path: str
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FolderWithFiles(FolderResponse):
    """Folder response with file count"""

    file_count: int = 0

    model_config = {"from_attributes": True}


class FolderTree(BaseModel):
    """Hierarchical folder structure"""

    id: int
    name: str
    description: Optional[str] = None
    path: str
    parent_id: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: datetime
    file_count: int = 0
    children: List["FolderTree"] = []

    model_config = {"from_attributes": True}


class FolderPath(BaseModel):
    """Folder path information"""

    id: int
    name: str
    path: str
    ancestors: List["FolderPathItem"] = []

    model_config = {"from_attributes": True}


class FolderPathItem(BaseModel):
    """Individual folder in a path"""

    id: int
    name: str

    model_config = {"from_attributes": True}


class FolderMoveRequest(BaseModel):
    """Request to move a folder to a new parent"""

    new_parent_id: Optional[int] = Field(
        None, description="New parent folder ID (null for root)"
    )


class FolderStats(BaseModel):
    """Folder statistics"""

    total_folders: int
    total_files: int
    total_size: int  # in bytes
    depth: int  # maximum folder depth


# Update FolderTree to handle self-reference
FolderTree.model_rebuild()
