from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from .auth import get_current_user
from ..models.user import User
from ..schemas.folder import (
    FolderCreate,
    FolderUpdate,
    FolderResponse,
    FolderTree,
    FolderMoveRequest,
    FolderStats,
    FolderWithFiles,
)
from ..services.folder_service import FolderService

router = APIRouter()


@router.get("/", response_model=List[FolderWithFiles])
async def get_folders(
    parent_id: Optional[int] = Query(
        None, description="Parent folder ID (null for root folders)"
    ),
    skip: int = Query(0, ge=0, description="Number of folders to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of folders to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get folders with optional parent filter"""
    folders = await FolderService.get_folders(db, parent_id, skip, limit)

    # Convert to response format with file counts
    folder_responses = []
    for folder in folders:
        folder_response = FolderWithFiles(
            id=folder.id,
            name=folder.name,
            description=folder.description,
            parent_id=folder.parent_id,
            path=folder.path,
            created_by=folder.created_by,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            file_count=len(folder.files) if folder.files else 0,
        )
        folder_responses.append(folder_response)

    return folder_responses


@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new folder"""
    folder = await FolderService.create_folder(db, folder_data, current_user.id)
    return folder


@router.get("/tree", response_model=List[FolderTree])
async def get_folder_tree(
    parent_id: Optional[int] = Query(
        None, description="Parent folder ID (null for full tree from root)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get hierarchical folder tree"""
    return await FolderService.get_folder_tree(db, parent_id)


@router.get("/stats", response_model=FolderStats)
async def get_folder_stats(
    folder_id: Optional[int] = Query(
        None, description="Folder ID (null for global stats)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get folder statistics"""
    return await FolderService.get_folder_stats(db, folder_id)


@router.get("/{folder_id}", response_model=FolderWithFiles)
async def get_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get folder by ID"""
    folder = await FolderService.get_folder_by_id(db, folder_id)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )

    return FolderWithFiles(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        parent_id=folder.parent_id,
        path=folder.path,
        created_by=folder.created_by,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        file_count=len(folder.files) if folder.files else 0,
    )


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: int,
    folder_update: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update folder"""
    folder = await FolderService.update_folder(db, folder_id, folder_update)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )

    return folder


@router.post("/{folder_id}/move", response_model=FolderResponse)
async def move_folder(
    folder_id: int,
    move_request: FolderMoveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move folder to a new parent"""
    folder = await FolderService.move_folder(db, folder_id, move_request.new_parent_id)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )

    return folder


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    recursive: bool = Query(
        False, description="Delete folder and all contents recursively"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete folder"""
    success = await FolderService.delete_folder(db, folder_id, recursive)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )

    return {"message": "Folder deleted successfully"}


@router.get("/{folder_id}/children", response_model=List[FolderWithFiles])
async def get_folder_children(
    folder_id: int,
    skip: int = Query(0, ge=0, description="Number of folders to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of folders to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get direct children of a folder"""
    # First check if parent folder exists
    parent_folder = await FolderService.get_folder_by_id(db, folder_id)
    if not parent_folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parent folder not found"
        )

    folders = await FolderService.get_folders(db, folder_id, skip, limit)

    # Convert to response format with file counts
    folder_responses = []
    for folder in folders:
        folder_response = FolderWithFiles(
            id=folder.id,
            name=folder.name,
            description=folder.description,
            parent_id=folder.parent_id,
            path=folder.path,
            created_by=folder.created_by,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            file_count=len(folder.files) if folder.files else 0,
        )
        folder_responses.append(folder_response)

    return folder_responses


@router.get("/{folder_id}/tree", response_model=List[FolderTree])
async def get_folder_subtree(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get folder subtree starting from specified folder"""
    # First check if folder exists
    folder = await FolderService.get_folder_by_id(db, folder_id)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
        )

    return await FolderService.get_folder_tree(db, folder_id)
