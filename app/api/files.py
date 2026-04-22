import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.database import get_db
from ..core.config import settings
from ..core.minio_client import minio_client
from ..models.file import File as FileModel
from ..models.user import User
from ..schemas.file import FileMetadata, FileUploadResponse
from .auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return filename.split(".")[-1].lower() if "." in filename else ""


@router.get("/", response_model=List[FileMetadata])
async def get_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    incident_id: Optional[int] = Query(None),
    folder_id: Optional[int] = Query(None),
):
    # Security: Only return files from the current user's tenant
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to view files",
        )
    
    query = select(FileModel).where(FileModel.tenant_id == current_user.tenant_id)

    if incident_id:
        query = query.where(FileModel.incident_id == incident_id)

    if folder_id:
        query = query.where(FileModel.folder_id == folder_id)

    query = query.offset(skip).limit(limit).order_by(FileModel.created_at.desc())

    result = await db.execute(query)
    files = result.scalars().all()

    return files


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    incident_id: Optional[int] = None,
    folder_id: Optional[int] = None,
):
    logger.info(f"File upload started: {file.filename} by user {current_user.id}")

    # Validate filename exists
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required"
        )

    # Security: Ensure user belongs to a tenant
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to upload files",
        )

    # Validate folder exists if folder_id is provided and belongs to same tenant
    if folder_id:
        from ..models.folder import Folder

        folder_result = await db.execute(
            select(Folder).where(
                Folder.id == folder_id,
                Folder.tenant_id == current_user.tenant_id
            )
        )
        folder = folder_result.scalar_one_or_none()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
            )

    # Validate file size
    if file.size and file.size > settings.max_file_size:
        # Convert bytes to GB for user-friendly error message
        max_size_gb = settings.max_file_size / (1024 * 1024 * 1024)
        logger.warning(
            f"File too large: {file.size} bytes (max: {settings.max_file_size})"
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {max_size_gb:.1f}GB ({settings.max_file_size} bytes)",
        )

    # Validate file extension (unless all extensions are allowed)
    file_extension = get_file_extension(file.filename)
    if not settings.allow_all_extensions:
        if file_extension not in settings.allowed_extensions:
            logger.warning(f"File type not allowed: {file_extension}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(settings.allowed_extensions)}",
            )

    # Generate unique filename for MinIO
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{file_extension}" if file_extension else file_id

    try:
        # Get folder path for MinIO storage if folder_id is provided
        # Note: Folder was already validated above with tenant check
        folder_path = None
        if folder_id:
            from ..models.folder import Folder

            folder_result = await db.execute(
                select(Folder).where(
                    Folder.id == folder_id,
                    Folder.tenant_id == current_user.tenant_id
                )
            )
            folder = folder_result.scalar_one_or_none()
            if folder:
                folder_path = folder.path.lstrip(
                    "/"
                )  # Remove leading slash for MinIO path

        # Upload to MinIO
        logger.info(f"Uploading file to MinIO: {filename} (folder: {folder_path})")
        object_name, file_size = await minio_client.upload_file(
            file, filename, folder_path
        )
        logger.info(f"File uploaded successfully to MinIO, size: {file_size} bytes")

        # Save file metadata to database
        # Security: Set tenant_id from current_user to ensure tenant isolation
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to a tenant to upload files",
            )
        
        db_file = FileModel(
            filename=filename,
            original_filename=file.filename,
            file_path=object_name,  # Store MinIO object name instead of local path
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            uploaded_by=current_user.id,
            tenant_id=current_user.tenant_id,  # Ensure tenant isolation
            incident_id=incident_id,
            folder_id=folder_id,
        )

        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)

        logger.info(f"File upload completed: {file.filename} (ID: {db_file.id})")
        return FileUploadResponse(message="File uploaded successfully", file=db_file)

    except HTTPException:
        # Re-raise HTTP exceptions (from MinIO client)
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}", exc_info=True)
        # Try to clean up from MinIO if database operation fails
        try:
            if "object_name" in locals():
                minio_client.delete_file(object_name)
        except Exception:
            pass  # Ignore cleanup errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed",
        )


@router.get("/{file_id}")
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Security: Only allow access to files from the current user's tenant
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to download files",
        )
    
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.tenant_id == current_user.tenant_id
        )
    )
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Check if file exists in MinIO
    if not minio_client.file_exists(file_record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage"
        )

    # Generate presigned URL for download
    try:
        download_url = minio_client.get_presigned_download_url(
            object_name=file_record.file_path, filename=file_record.original_filename
        )

        # Return a redirect to the presigned URL
        return RedirectResponse(url=download_url, status_code=302)

    except Exception as e:
        logger.error(f"Failed to generate download URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL",
        )


@router.options("/{file_id}")
async def download_file_options(file_id: int):
    """Handle CORS preflight requests for file downloads"""
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Security: Only allow deletion of files from the current user's tenant
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to delete files",
        )
    
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.tenant_id == current_user.tenant_id
        )
    )
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Check permissions - only admin/operator or file uploader can delete
    if (
        current_user.role not in ["admin", "operator"]
        and file_record.uploaded_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this file",
        )

    # Delete file from MinIO
    try:
        minio_client.delete_file(file_record.file_path)
        logger.info(f"File deleted from MinIO: {file_record.file_path}")
    except Exception as e:
        logger.warning(f"Failed to delete file from MinIO: {str(e)}")
        # Continue with database deletion even if MinIO deletion fails

    # Delete record from database
    await db.delete(file_record)
    await db.commit()

    return {"message": "File deleted successfully"}


@router.get("/{file_id}/metadata", response_model=FileMetadata)
async def get_file_metadata(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Security: Only allow access to files from the current user's tenant
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to view file metadata",
        )
    
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.tenant_id == current_user.tenant_id
        )
    )
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return file_record


@router.get("/{file_id}/download-url")
async def get_download_url(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a presigned download URL for the file (useful for frontend direct downloads)"""
    # Security: Only allow access to files from the current user's tenant
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to get download URLs",
        )
    
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.tenant_id == current_user.tenant_id
        )
    )
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Check if file exists in MinIO
    if not minio_client.file_exists(file_record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage"
        )

    # Generate presigned URL for download
    try:
        download_url = minio_client.get_presigned_download_url(
            object_name=file_record.file_path, filename=file_record.original_filename
        )

        return {
            "download_url": download_url,
            "expires_in": settings.minio_presigned_url_expiry,
            "filename": file_record.original_filename,
        }

    except Exception as e:
        logger.error(f"Failed to generate download URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL",
        )


@router.put("/{file_id}/move")
async def move_file_to_folder(
    file_id: int,
    folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move file to a different folder"""
    # Security: Only allow access to files from the current user's tenant
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to move files",
        )
    
    # Get the file
    result = await db.execute(
        select(FileModel).where(
            FileModel.id == file_id,
            FileModel.tenant_id == current_user.tenant_id
        )
    )
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Check permissions - only admin/operator or file uploader can move
    if (
        current_user.role not in ["admin", "operator"]
        and file_record.uploaded_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to move this file",
        )

    # Validate folder exists if folder_id is provided
    if folder_id:
        from ..models.folder import Folder

        folder_result = await db.execute(select(Folder).where(Folder.id == folder_id))
        folder = folder_result.scalar_one_or_none()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
            )

    # Update file folder
    file_record.folder_id = folder_id
    await db.commit()
    await db.refresh(file_record)

    return {"message": "File moved successfully", "file": file_record}


@router.get("/folder/{folder_id}", response_model=List[FileMetadata])
async def get_files_in_folder(
    folder_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all files in a specific folder"""
    # Security: Only allow access to folders and files from the current user's tenant
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to view files",
        )
    
    # First check if folder exists and belongs to same tenant
    from ..models.folder import Folder

    folder_result = await db.execute(
        select(Folder).where(
            Folder.id == folder_id,
            Folder.tenant_id == current_user.tenant_id
        )
    )
    folder = folder_result.scalar_one_or_none()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )

    # Get files in folder (already filtered by tenant_id in FileModel)
    query = select(FileModel).where(
        FileModel.folder_id == folder_id,
        FileModel.tenant_id == current_user.tenant_id
    )
    query = query.offset(skip).limit(limit).order_by(FileModel.created_at.desc())

    result = await db.execute(query)
    files = result.scalars().all()

    return files
