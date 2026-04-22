"""
API endpoint for receiving Frigate webhook events.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.config import settings
from ..core.tenant import tenant_service
from ..schemas.frigate_event import FrigateWebhookPayload, FrigateEventResponse
from ..services.frigate_event_service import FrigateEventService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook", response_model=FrigateEventResponse, status_code=status.HTTP_201_CREATED)
async def receive_frigate_webhook(
    request: Request,
    payload: FrigateWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive webhook events from Frigate.
    
    This endpoint processes Frigate webhook events and creates/updates Event records.
    Frigate should be configured to send webhooks to this endpoint.
    
    Example Frigate config:
    ```yaml
    webhooks:
      - url: http://your-api-url/api/v1/frigate/webhook
        events:
          - new
          - update
          - end
    ```
    """
    try:
        # Get tenant_id from context if available (set by middleware)
        tenant_id = None
        if tenant_service:
            tenant_id = tenant_service.get_tenant_id()
        
        # Get Frigate base URL from settings or request
        frigate_base_url = getattr(settings, "frigate_base_url", None)
        if not frigate_base_url:
            # Try to infer from request
            frigate_base_url = None
        
        # Process the Frigate event
        event = await FrigateEventService.process_frigate_event(
            db=db,
            payload=payload,
            frigate_base_url=frigate_base_url,
            tenant_id=tenant_id,
        )
        
        logger.info(
            f"Successfully processed Frigate event {payload.id} "
            f"(type: {payload.type}, camera: {payload.camera})"
        )
        
        return FrigateEventResponse(
            success=True,
            event_id=event.id,
            message=f"Event {payload.type} processed successfully",
            camera_id=event.camera_id,
            tenant_id=event.tenant_id,
        )
        
    except ValueError as e:
        logger.error(f"Error processing Frigate event {payload.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"Unexpected error processing Frigate event {payload.id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Frigate event",
        )


@router.get("/health")
async def frigate_webhook_health():
    """Health check endpoint for Frigate webhook"""
    return {"status": "ok", "service": "frigate-webhook"}

