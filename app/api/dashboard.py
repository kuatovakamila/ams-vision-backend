from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..core.database import get_db
from ..models.user import User
from ..models.camera import Camera
from ..models.incident import Incident
from ..models.event import Event
from ..models.file import File
from ..schemas.dashboard import DashboardStats, QuickStats
from .auth import get_current_user

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Get total counts
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()

    total_cameras_result = await db.execute(select(func.count(Camera.id)))
    total_cameras = total_cameras_result.scalar()

    active_cameras_result = await db.execute(
        select(func.count(Camera.id)).where(Camera.status == "active")
    )
    active_cameras = active_cameras_result.scalar()

    total_incidents_result = await db.execute(select(func.count(Incident.id)))
    total_incidents = total_incidents_result.scalar()

    open_incidents_result = await db.execute(
        select(func.count(Incident.id)).where(Incident.status == "open")
    )
    open_incidents = open_incidents_result.scalar()

    # Get events statistics
    total_events_result = await db.execute(select(func.count(Event.id)))
    total_events = total_events_result.scalar()

    entrance_events_result = await db.execute(
        select(func.count(Event.id)).where(Event.event_type == "entrance")
    )
    entrance_events = entrance_events_result.scalar()

    exit_events_result = await db.execute(
        select(func.count(Event.id)).where(Event.event_type == "exit")
    )
    exit_events = exit_events_result.scalar()

    total_files_result = await db.execute(select(func.count(File.id)))
    total_files = total_files_result.scalar()

    return DashboardStats(
        total_users=total_users,
        total_cameras=total_cameras,
        active_cameras=active_cameras,
        total_incidents=total_incidents,
        open_incidents=open_incidents,
        total_events=total_events,
        entrance_events=entrance_events,
        exit_events=exit_events,
        total_files=total_files,
        system_uptime="Running",
        last_updated=datetime.now().isoformat(),
    )


@router.get("/incidents/summary")
async def get_incidents_summary(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Get incident counts by status
    status_counts = {}
    for status in ["open", "investigating", "resolved", "closed"]:
        result = await db.execute(
            select(func.count(Incident.id)).where(Incident.status == status)
        )
        status_counts[status] = result.scalar()

    # Get incident counts by type
    types_result = await db.execute(
        select(Incident.incident_type, func.count(Incident.id)).group_by(
            Incident.incident_type
        )
    )
    types_data = types_result.all()
    incidents_by_type = [{"type": row[0], "count": row[1]} for row in types_data]

    # Get incident counts by priority
    priorities_result = await db.execute(
        select(Incident.priority, func.count(Incident.id)).group_by(Incident.priority)
    )
    priorities_data = priorities_result.all()
    incidents_by_priority = [
        {"priority": row[0], "count": row[1]} for row in priorities_data
    ]

    total_incidents = sum(status_counts.values())

    return {
        "total_incidents": total_incidents,
        "open_incidents": status_counts.get("open", 0),
        "investigating_incidents": status_counts.get("investigating", 0),
        "resolved_incidents": status_counts.get("resolved", 0),
        "closed_incidents": status_counts.get("closed", 0),
        "incidents_by_type": incidents_by_type,
        "incidents_by_priority": incidents_by_priority,
    }


@router.get("/cameras/summary")
async def get_cameras_summary(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    total_result = await db.execute(select(func.count(Camera.id)))
    total_cameras = total_result.scalar()

    active_result = await db.execute(
        select(func.count(Camera.id)).where(Camera.status == "active")
    )
    active_cameras = active_result.scalar()

    inactive_cameras = total_cameras - active_cameras

    # Get cameras by location
    locations_result = await db.execute(
        select(Camera.location, func.count(Camera.id)).group_by(Camera.location)
    )
    locations_data = locations_result.all()
    cameras_by_location = [
        {"location": row[0], "count": row[1]} for row in locations_data
    ]

    return {
        "total_cameras": total_cameras,
        "active_cameras": active_cameras,
        "inactive_cameras": inactive_cameras,
        "cameras_by_location": cameras_by_location,
    }


@router.get("/employees/summary")
async def get_employees_summary(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Only admin can view employee summary
    if current_user.role != "admin":
        return {
            "total_employees": 1,
            "active_employees": 1,
            "employees_by_role": [{"role": current_user.role, "count": 1}],
        }

    total_result = await db.execute(select(func.count(User.id)))
    total_employees = total_result.scalar()

    active_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_employees = active_result.scalar()

    # Get employees by role
    roles_result = await db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    )
    roles_data = roles_result.all()
    employees_by_role = [{"role": row[0], "count": row[1]} for row in roles_data]

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "employees_by_role": employees_by_role,
    }


@router.get("/quick-stats", response_model=QuickStats)
async def get_quick_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Cameras stats
    total_cameras_result = await db.execute(select(func.count(Camera.id)))
    total_cameras = total_cameras_result.scalar()

    active_cameras_result = await db.execute(
        select(func.count(Camera.id)).where(Camera.status == "active")
    )
    active_cameras = active_cameras_result.scalar()

    # Incidents stats
    total_incidents_result = await db.execute(select(func.count(Incident.id)))
    total_incidents = total_incidents_result.scalar()

    open_incidents_result = await db.execute(
        select(func.count(Incident.id)).where(Incident.status == "open")
    )
    open_incidents = open_incidents_result.scalar()

    # Events stats
    total_events_result = await db.execute(select(func.count(Event.id)))
    total_events = total_events_result.scalar()

    entrance_events_result = await db.execute(
        select(func.count(Event.id)).where(Event.event_type == "entrance")
    )
    entrance_events = entrance_events_result.scalar()

    exit_events_result = await db.execute(
        select(func.count(Event.id)).where(Event.event_type == "exit")
    )
    exit_events = exit_events_result.scalar()

    # Users stats (only for admin)
    if current_user.role == "admin":
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar()

        active_users_result = await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_users_result.scalar()
    else:
        total_users = 1
        active_users = 1

    # Files stats
    total_files_result = await db.execute(select(func.count(File.id)))
    total_files = total_files_result.scalar()

    return QuickStats(
        cameras={
            "total": total_cameras,
            "active": active_cameras,
            "inactive": total_cameras - active_cameras,
        },
        incidents={
            "total": total_incidents,
            "open": open_incidents,
            "closed": total_incidents - open_incidents,
        },
        events={
            "total": total_events,
            "entrance": entrance_events,
            "exit": exit_events,
        },
        users={
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
        },
        files={"total": total_files},
    )
