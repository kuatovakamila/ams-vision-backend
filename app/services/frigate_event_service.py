"""
Service for processing Frigate webhook events and converting them to Event records.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..models.event import Event
from ..models.camera import Camera
from ..schemas.frigate_event import FrigateWebhookPayload, FrigateEventCreate

logger = logging.getLogger(__name__)


class FrigateEventService:
    """Service for processing Frigate events"""

    @staticmethod
    async def find_camera_by_name(
        db: AsyncSession, camera_name: str, tenant_id: Optional[int] = None
    ) -> Optional[Camera]:
        """
        Find camera by name (matching Frigate camera name).
        Optionally filter by tenant_id for security.
        """
        query = select(Camera).where(Camera.name == camera_name)
        
        if tenant_id is not None:
            query = query.where(Camera.tenant_id == tenant_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def find_existing_event(
        db: AsyncSession, frigate_event_id: str
    ) -> Optional[Event]:
        """Find existing event by Frigate event ID"""
        result = await db.execute(
            select(Event).where(Event.frigate_event_id == frigate_event_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def extract_object_type(after_data: Dict[str, Any]) -> Optional[str]:
        """Extract object type from Frigate event data"""
        # Try multiple fields where object type might be stored
        if "label" in after_data:
            return after_data["label"]
        if "type" in after_data:
            return after_data["type"]
        if "top_attr" in after_data:
            return after_data["top_attr"]
        return None

    @staticmethod
    def extract_confidence(after_data: Dict[str, Any]) -> Optional[float]:
        """Extract confidence score from Frigate event data"""
        if "score" in after_data:
            return float(after_data["score"])
        if "top_score" in after_data:
            return float(after_data["top_score"])
        return None

    @staticmethod
    def build_snapshot_url(frigate_base_url: str, camera: str, event_id: str) -> Optional[str]:
        """Build snapshot URL from Frigate base URL"""
        if not frigate_base_url:
            return None
        # Remove trailing slash if present
        base_url = frigate_base_url.rstrip("/")
        return f"{base_url}/api/events/{event_id}/snapshot.jpg"

    @staticmethod
    def build_clip_url(frigate_base_url: str, camera: str, event_id: str) -> Optional[str]:
        """Build clip URL from Frigate base URL"""
        if not frigate_base_url:
            return None
        # Remove trailing slash if present
        base_url = frigate_base_url.rstrip("/")
        return f"{base_url}/api/events/{event_id}/clip.mp4"

    @staticmethod
    def parse_frigate_timestamp(frame_time: float) -> datetime:
        """Convert Frigate frame_time (float) to datetime"""
        return datetime.fromtimestamp(frame_time)

    @staticmethod
    def determine_event_type(frigate_type: str, after_data: Dict[str, Any]) -> str:
        """
        Determine our event_type from Frigate event.
        Maps Frigate events to our event types: detection, motion, alarm, etc.
        """
        # Check for alarm indicators
        if after_data.get("false_positive") is False and after_data.get("score", 0) > 0.7:
            # High confidence detection - could be an alarm
            if after_data.get("entered_zones"):
                return "alarm"
            return "detection"
        
        # Motion detection
        if frigate_type == "new" and not after_data.get("label"):
            return "motion"
        
        # Default to detection
        return "detection"

    @staticmethod
    async def process_frigate_event(
        db: AsyncSession,
        payload: FrigateWebhookPayload,
        frigate_base_url: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Event:
        """
        Process a Frigate webhook event and create/update an Event record.
        
        Args:
            db: Database session
            payload: Frigate webhook payload
            frigate_base_url: Base URL for Frigate (for building snapshot/clip URLs)
            tenant_id: Optional tenant ID for security filtering
            
        Returns:
            Created or updated Event record
        """
        # Find camera by name
        camera = await FrigateEventService.find_camera_by_name(
            db, payload.camera, tenant_id=tenant_id
        )
        
        if not camera:
            logger.warning(
                f"Camera '{payload.camera}' not found in database. "
                f"Event will be created without camera_id."
            )
        
        # Check if event already exists (for updates)
        existing_event = await FrigateEventService.find_existing_event(
            db, payload.id
        )
        
        # Extract data from 'after' field
        if isinstance(payload.after, BaseModel):
            after_data = payload.after.model_dump() if hasattr(payload.after, 'model_dump') else payload.after.dict()
        else:
            after_data = payload.after
        
        # Extract object type and confidence
        object_type = FrigateEventService.extract_object_type(after_data)
        confidence = FrigateEventService.extract_confidence(after_data)
        
        # Build URLs
        snapshot_url = None
        clip_url = None
        if frigate_base_url:
            snapshot_url = FrigateEventService.build_snapshot_url(
                frigate_base_url, payload.camera, payload.id
            )
            if after_data.get("has_clip"):
                clip_url = FrigateEventService.build_clip_url(
                    frigate_base_url, payload.camera, payload.id
                )
        
        # Parse timestamp
        frigate_timestamp = FrigateEventService.parse_frigate_timestamp(payload.frame_time)
        
        # Determine event type
        event_type = FrigateEventService.determine_event_type(
            payload.type, after_data
        )
        
        # Prepare metadata (store zones, regions, etc.)
        metadata = {
            "zones": after_data.get("zones"),
            "entered_zones": after_data.get("entered_zones"),
            "current_zones": after_data.get("current_zones"),
            "region": after_data.get("region"),
            "box": after_data.get("box"),
            "area": after_data.get("area"),
            "ratio": after_data.get("ratio"),
            "false_positive": after_data.get("false_positive"),
            "retained": after_data.get("retained"),
            "stationary": after_data.get("stationary"),
            "motionless_count": after_data.get("motionless_count"),
            "position_changes": after_data.get("position_changes"),
            "attributes": after_data.get("attributes"),
        }
        
        # Set tenant_id from camera if available
        tenant_id = camera.tenant_id if camera else tenant_id
        
        if not tenant_id:
            raise ValueError(
                f"Cannot determine tenant_id for event. "
                f"Camera '{payload.camera}' not found or has no tenant_id."
            )
        
        # Create or update event
        if existing_event:
            # Update existing event
            existing_event.frigate_type = payload.type
            existing_event.object_type = object_type
            existing_event.confidence = confidence
            existing_event.snapshot_url = snapshot_url
            existing_event.clip_url = clip_url
            existing_event.event_metadata = metadata
            existing_event.frigate_timestamp = frigate_timestamp
            existing_event.event_type = event_type
            
            await db.commit()
            await db.refresh(existing_event)
            
            logger.info(
                f"Updated event {existing_event.id} from Frigate event {payload.id}"
            )
            return existing_event
        else:
            # Create new event
            new_event = Event(
                frigate_event_id=payload.id,
                frigate_type=payload.type,
                event_type=event_type,
                object_type=object_type,
                confidence=confidence,
                snapshot_url=snapshot_url,
                clip_url=clip_url,
                event_metadata=metadata,
                frigate_timestamp=frigate_timestamp,
                camera_id=camera.id if camera else None,
                location=camera.location if camera else None,
                tenant_id=tenant_id,
            )
            
            db.add(new_event)
            await db.commit()
            await db.refresh(new_event)
            
            logger.info(
                f"Created event {new_event.id} from Frigate event {payload.id} "
                f"(camera: {payload.camera}, type: {event_type}, object: {object_type})"
            )
            return new_event

