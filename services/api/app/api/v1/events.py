from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

try:
    from app.api.dependencies import get_db
except ImportError:
    async def get_db():
        yield None

from app.db.models import Event as DBEvent
from app.api.auth import User, get_operator
from app.api.audit import log_audit_event
from app.schemas.event import EventListResponse, EventResponse, Event

router = APIRouter()

def db_event_to_pydantic(db_event: DBEvent) -> Event:
    return Event(
        event_id=db_event.event_id,
        type=db_event.type,
        camera_id=db_event.camera_id,
        timestamp=db_event.timestamp.isoformat() if db_event.timestamp else None,
        track_id=db_event.track_id,
        confidence=db_event.confidence,
        severity=db_event.severity,
        status=db_event.status or "NEW",
        media_ref=db_event.media_ref,
        metadata=db_event.metadata_ or {}
    )

@router.get("/", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    camera_id: str = None,
    event_type: str = None,
    db: AsyncSession = Depends(get_db)
):
    if not db:
        return EventListResponse(data=[], total=0, page=page, size=size)
        
    stmt = select(DBEvent)
    if camera_id:
        stmt = stmt.where(DBEvent.camera_id == camera_id)
    if event_type:
        stmt = stmt.where(DBEvent.type == event_type)
        
    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0
    
    # Paginate
    stmt = stmt.order_by(DBEvent.timestamp.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    
    events = [db_event_to_pydantic(row) for row in result.scalars().all()]
    
    return EventListResponse(
        data=events,
        total=total,
        page=page,
        size=size
    )

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    if not db:
        return None
    stmt = select(DBEvent).where(DBEvent.event_id == event_id)
    result = await db.execute(stmt)
    db_event = result.scalars().first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    return EventResponse(data=db_event_to_pydantic(db_event))

from pydantic import BaseModel

class EventStatusUpdate(BaseModel):
    status: str

@router.patch("/{event_id}", response_model=EventResponse)
async def update_event_status(
    event_id: str, 
    update: EventStatusUpdate, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_operator)
):
    if not db:
        return None
    stmt = select(DBEvent).where(DBEvent.event_id == event_id)
    result = await db.execute(stmt)
    db_event = result.scalars().first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    db_event.status = update.status
    
    # Audit log
    await log_audit_event(
        db=db,
        actor=user.username,
        action="UPDATE_STATUS",
        resource_type="Event",
        resource_id=event_id,
        metadata={"new_status": update.status}
    )
    
    await db.commit()
    await db.refresh(db_event)
    
    return EventResponse(data=db_event_to_pydantic(db_event))
