from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from ..core.database import get_db
from ..core.dependencies import (
    RequireCameraCreate,
    RequireCameraUpdate,
    RequireCameraDelete,
    RequireCameraRead,
)
from ..models.camera import Camera
from ..models.user import User
from ..schemas.camera import (
    CameraResponse,
    CameraCreate,
    CameraUpdate,
    CameraStatusUpdate,
    CameraStats,
)
from .auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[CameraResponse])
async def get_cameras(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    query = select(Camera)

    # Apply filters
    if search:
        search_filter = or_(
            Camera.name.ilike(f"%{search}%"),
            Camera.location.ilike(f"%{search}%"),
            Camera.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if location:
        query = query.where(Camera.location.ilike(f"%{location}%"))

    if status:
        query = query.where(Camera.status == status)

    query = query.offset(skip).limit(limit).order_by(Camera.created_at.desc())

    result = await db.execute(query)
    cameras = result.scalars().all()

    return cameras


@router.post("/", response_model=CameraResponse)
async def create_camera(
    camera_data: CameraCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireCameraCreate),
):
    db_camera = Camera(
        name=camera_data.name,
        location=camera_data.location,
        description=camera_data.description,
        status=camera_data.status,
        ip_address=camera_data.ip_address,
        stream_url=camera_data.stream_url,
    )

    db.add(db_camera)
    await db.commit()
    await db.refresh(db_camera)

    return db_camera


@router.get("/count", response_model=CameraStats)
async def get_camera_count(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Total cameras
    total_result = await db.execute(select(func.count(Camera.id)))
    total_cameras = total_result.scalar()

    # Active cameras
    active_result = await db.execute(
        select(func.count(Camera.id)).where(Camera.status == "active")
    )
    active_cameras = active_result.scalar()

    # Inactive cameras
    inactive_cameras = total_cameras - active_cameras

    return CameraStats(
        total_cameras=total_cameras,
        active_cameras=active_cameras,
        inactive_cameras=inactive_cameras,
    )


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found"
        )

    return camera


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    camera_update: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireCameraUpdate),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found"
        )

    # Update camera fields
    for field, value in camera_update.dict(exclude_unset=True).items():
        setattr(camera, field, value)

    await db.commit()
    await db.refresh(camera)

    return camera


@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireCameraDelete),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found"
        )

    await db.delete(camera)
    await db.commit()

    return {"message": "Camera deleted successfully"}


@router.put("/{camera_id}/status", response_model=CameraResponse)
async def update_camera_status(
    camera_id: int,
    status_update: CameraStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireCameraUpdate),
):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    camera = result.scalar_one_or_none()

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found"
        )

    camera.status = status_update.status
    await db.commit()
    await db.refresh(camera)

    return camera
