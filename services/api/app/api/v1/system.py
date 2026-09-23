from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Dict, Any

try:
    from app.api.dependencies import get_db, redis_client
except ImportError:
    async def get_db():
        yield None
    redis_client = None

from app.db.models import Camera, Event

router = APIRouter()

@router.get("/health")
async def get_system_health(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    # Determine DB Status
    db_status = "Failed"
    active_cameras = 0
    total_cameras = 0
    event_count = 0
    
    if db is not None:
        try:
            # Query db for active cameras
            active_stmt = select(func.count()).select_from(Camera).where(Camera.enabled == True)
            active_cameras = await db.scalar(active_stmt) or 0
            
            total_stmt = select(func.count()).select_from(Camera)
            total_cameras = await db.scalar(total_stmt) or 0
            
            events_stmt = select(func.count()).select_from(Event)
            event_count = await db.scalar(events_stmt) or 0
            
            db_status = "Healthy"
        except Exception:
            db_status = "Failed"

    # Determine Redis Status
    redis_status = "Failed"
    try:
        # In prototype, redis_client might be mock or real. We just assume healthy if defined.
        if redis_client is not None:
            # ping redis
            await redis_client.ping()
            redis_status = "Healthy"
        else:
            redis_status = "Unavailable"
    except Exception:
        redis_status = "Failed"
        
    return {
        "status": "Healthy" if db_status == "Healthy" else "Degraded",
        "metrics": {
            "active_cameras": active_cameras,
            "total_cameras": total_cameras,
            "inference_fps": "Unavailable",
            "cpu_usage": "Unavailable",
            "queue_depth": "Unavailable",
            "total_events": event_count
        },
        "services": {
            "FastAPI": "Healthy",
            "PostgreSQL": db_status,
            "Redis": redis_status,
            "Qdrant": "Unavailable",
            "MinIO": "Unavailable"
        }
    }
