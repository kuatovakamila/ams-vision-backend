from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# Base schemas
class FileBase(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    incident_id: Optional[int] = None
    folder_id: Optional[int] = None


class FileCreate(FileBase):
    file_path: str
    uploaded_by: Optional[int] = None


class FileResponse(FileBase):
    id: int
    file_path: str
    uploaded_by: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FileMetadata(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    uploaded_by: Optional[int] = None
    incident_id: Optional[int] = None
    folder_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FileWithFolder(FileMetadata):
    """File metadata with folder information"""

    folder_path: Optional[str] = None
    folder_name: Optional[str] = None

    model_config = {"from_attributes": True}


class FileUploadResponse(BaseModel):
    message: str
    file: FileResponse
