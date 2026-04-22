from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
import csv
import io
from datetime import datetime

from ..core.database import get_db
from ..core.dependencies import (
    RequireIncidentCreate,
    RequireIncidentUpdate,
    RequireIncidentDelete,
)
from ..models.incident import Incident
from ..models.user import User
from ..schemas.incident import (
    IncidentResponse,
    IncidentCreate,
    IncidentUpdate,
    IncidentType,
    IncidentSummary,
)
from .auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[IncidentResponse])
async def get_incidents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    incident_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
):
    query = select(Incident)

    # Apply filters
    if search:
        search_filter = or_(
            Incident.title.ilike(f"%{search}%"),
            Incident.description.ilike(f"%{search}%"),
            Incident.location.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if incident_type:
        query = query.where(Incident.incident_type == incident_type)

    if status:
        query = query.where(Incident.status == status)

    if priority:
        query = query.where(Incident.priority == priority)

    query = query.offset(skip).limit(limit).order_by(Incident.created_at.desc())

    result = await db.execute(query)
    incidents = result.scalars().all()

    return incidents


@router.post("/", response_model=IncidentResponse)
async def create_incident(
    incident_data: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireIncidentCreate),
):
    db_incident = Incident(
        title=incident_data.title,
        description=incident_data.description,
        incident_type=incident_data.incident_type,
        status=incident_data.status,
        priority=incident_data.priority,
        location=incident_data.location,
        camera_id=incident_data.camera_id,
        assigned_to=incident_data.assigned_to,
        reported_by=current_user.id,
    )

    db.add(db_incident)
    await db.commit()
    await db.refresh(db_incident)

    return db_incident


@router.get("/types", response_model=List[IncidentType])
async def get_incident_types(current_user: User = Depends(get_current_user)):
    # Predefined incident types
    types = [
        IncidentType(name="security_breach", description="Нарушение безопасности"),
        IncidentType(
            name="unauthorized_access", description="Несанкционированный доступ"
        ),
        IncidentType(name="equipment_failure", description="Отказ оборудования"),
        IncidentType(name="vandalism", description="Вандализм"),
        IncidentType(name="theft", description="Кража"),
        IncidentType(name="fire", description="Пожар"),
        IncidentType(name="medical_emergency", description="Медицинская помощь"),
        IncidentType(name="other", description="Прочее"),
    ]
    return types


@router.get("/export")
async def export_incidents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    format: str = Query("json", regex="^(json|csv)$"),
):
    result = await db.execute(select(Incident).order_by(Incident.created_at.desc()))
    incidents = result.scalars().all()

    incidents_data = [
        {
            "id": inc.id,
            "title": inc.title,
            "description": inc.description,
            "type": inc.incident_type,
            "status": inc.status,
            "priority": inc.priority,
            "location": inc.location,
            "created_at": inc.created_at.isoformat(),
            "updated_at": inc.updated_at.isoformat(),
        }
        for inc in incidents
    ]

    if format == "csv":
        # Create CSV content
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "id",
                "title",
                "description",
                "type",
                "status",
                "priority",
                "location",
                "created_at",
                "updated_at",
            ],
        )
        writer.writeheader()
        writer.writerows(incidents_data)
        csv_content = output.getvalue()
        output.close()

        # Return CSV as streaming response
        current_date = datetime.now().strftime("%d-%m-%Y")
        filename = f"incidents_{current_date}.csv"
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # Default JSON format
    return {"incidents": incidents_data, "total": len(incidents_data)}


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )

    return incident


@router.put("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: int,
    incident_update: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireIncidentUpdate),
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )

    # Update incident fields
    for field, value in incident_update.dict(exclude_unset=True).items():
        setattr(incident, field, value)

    await db.commit()
    await db.refresh(incident)

    return incident


@router.delete("/{incident_id}")
async def delete_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireIncidentDelete),
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found"
        )

    await db.delete(incident)
    await db.commit()

    return {"message": "Incident deleted successfully"}
