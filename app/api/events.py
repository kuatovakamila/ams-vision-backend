from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io

from ..models.event import Event
from ..models.user import User
from ..core.database import get_db
from ..api.auth import get_current_user
from ..schemas.event import (
    EventResponse,
    EventCreate,
    EventUpdate,
    EventType,
    EventSummary,
)

router = APIRouter()


@router.get("/", response_model=List[EventResponse])
async def get_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    camera_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    object_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get all events with optional filtering (tenant-aware)"""
    from ..core.tenant import tenant_service
    from ..models.user import User
    
    # Security: Only return events from the current user's tenant
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to view events",
        )
    
    query = select(Event).where(Event.tenant_id == current_user.tenant_id)

    # Apply search filter
    if search:
        query = query.where(or_(Event.location.ilike(f"%{search}%")))

    # Apply filters
    if event_type:
        query = query.where(Event.event_type == event_type)

    if camera_id:
        query = query.where(Event.camera_id == camera_id)

    if user_id:
        query = query.where(Event.user_id == user_id)
    
    if object_type:
        query = query.where(Event.object_type == object_type)

    query = query.offset(skip).limit(limit).order_by(Event.created_at.desc())

    result = await db.execute(query)
    events = result.scalars().all()

    return events


@router.post("/", response_model=EventResponse)
async def create_event(event_data: EventCreate, db: AsyncSession = Depends(get_db)):
    """Create a new event"""
    # Validate event type
    if event_data.event_type not in ["entrance", "exit"]:
        raise HTTPException(
            status_code=400, detail="Event type must be either 'entrance' or 'exit'"
        )

    db_event = Event(
        event_type=event_data.event_type,
        location=event_data.location,
        camera_id=event_data.camera_id,
        user_id=event_data.user_id,
    )

    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    return db_event


@router.get("/types", response_model=List[EventType])
async def get_event_types(db: AsyncSession = Depends(get_db)):
    """Get available event types"""
    return [
        EventType(name="entrance", description="Вход в помещение"),
        EventType(name="exit", description="Выход из помещения"),
    ]


@router.get("/summary", response_model=EventSummary)
async def get_events_summary(db: AsyncSession = Depends(get_db)):
    """Get events summary statistics"""
    # Get total events count
    total_events_result = await db.execute(select(func.count(Event.id)))
    total_events = total_events_result.scalar()

    # Get entrance events count
    entrance_events_result = await db.execute(
        select(func.count(Event.id)).where(Event.event_type == "entrance")
    )
    entrance_events = entrance_events_result.scalar()

    # Get exit events count
    exit_events_result = await db.execute(
        select(func.count(Event.id)).where(Event.event_type == "exit")
    )
    exit_events = exit_events_result.scalar()

    # Get events by type
    events_by_type = [
        {"type": "entrance", "count": entrance_events},
        {"type": "exit", "count": exit_events},
    ]

    return EventSummary(
        total_events=total_events,
        entrance_events=entrance_events,
        exit_events=exit_events,
        events_by_type=events_by_type,
    )


@router.get("/export")
async def export_events(
    event_type: Optional[str] = Query(None),
    camera_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export events data as CSV"""
    query = select(Event)

    if event_type:
        query = query.where(Event.event_type == event_type)

    if camera_id:
        query = query.where(Event.camera_id == camera_id)

    result = await db.execute(query.order_by(Event.created_at.desc()))
    events = result.scalars().all()

    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV header
    writer.writerow(
        ["ID", "Type", "Location", "Camera ID", "User ID", "Created At", "Updated At"]
    )

    # Write event data
    for event in events:
        writer.writerow(
            [
                event.id,
                event.event_type,
                event.location,
                event.camera_id,
                event.user_id,
                event.created_at.isoformat() if event.created_at else "",
                event.updated_at.isoformat() if event.updated_at else "",
            ]
        )

    # Get CSV content
    csv_content = output.getvalue()
    output.close()

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"events_export_{timestamp}.csv"

    # Return CSV as streaming response
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific event by ID"""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int, event_update: EventUpdate, db: AsyncSession = Depends(get_db)
):
    """Update an existing event"""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Validate event type if being updated
    if event_update.event_type and event_update.event_type not in ["entrance", "exit"]:
        raise HTTPException(
            status_code=400, detail="Event type must be either 'entrance' or 'exit'"
        )

    # Update event fields
    for field, value in event_update.dict(exclude_unset=True).items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)

    return event


@router.delete("/{event_id}")
async def delete_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an event"""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await db.delete(event)
    await db.commit()

    return {"message": "Event deleted successfully"}
