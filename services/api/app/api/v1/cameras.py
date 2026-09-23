from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from typing import List
import asyncio
import os
from fastapi.responses import StreamingResponse
try:
    from app.api.dependencies import get_db
except ImportError:
    async def get_db():
        yield None

from app.db.models import Camera as DBCamera
from app.schemas.camera import Camera, CameraCreate, CameraUpdate
from app.api.auth import User, get_admin
from app.api.audit import log_audit_event

router = APIRouter()

@router.get("/", response_model=List[Camera])
async def list_cameras(db: AsyncSession = Depends(get_db)):
    if not db:
        return []
    result = await db.execute(select(DBCamera))
    return result.scalars().all()

@router.post("/", response_model=Camera, status_code=201)
async def create_camera(
    camera: CameraCreate, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_admin)
):
    if not db:
        return None
    stmt = select(DBCamera).where(DBCamera.id == camera.id)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Camera already exists")
        
    db_camera = DBCamera(**camera.model_dump())
    db.add(db_camera)
    
    await log_audit_event(
        db=db,
        actor=user.username,
        action="CREATE",
        resource_type="Camera",
        resource_id=camera.id,
        metadata=camera.model_dump()
    )
    
    await db.commit()
    await db.refresh(db_camera)
    return db_camera

@router.get("/{camera_id}", response_model=Camera)
async def get_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    if not db:
        return None
    stmt = select(DBCamera).where(DBCamera.id == camera_id)
    result = await db.execute(stmt)
    db_camera = result.scalars().first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return db_camera

@router.put("/{camera_id}", response_model=Camera)
async def update_camera(
    camera_id: str, 
    camera_update: CameraUpdate, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_admin)
):
    if not db:
        return None
    stmt = select(DBCamera).where(DBCamera.id == camera_id)
    result = await db.execute(stmt)
    db_camera = result.scalars().first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    update_data = camera_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_camera, key, value)
        
    await log_audit_event(
        db=db,
        actor=user.username,
        action="UPDATE",
        resource_type="Camera",
        resource_id=camera_id,
        metadata=update_data
    )
        
    await db.commit()
    await db.refresh(db_camera)
    return db_camera

@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: str, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_admin)
):
    if not db:
        return
    stmt = select(DBCamera).where(DBCamera.id == camera_id)
    result = await db.execute(stmt)
    db_camera = result.scalars().first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    await db.delete(db_camera)
    
    await log_audit_event(
        db=db,
        actor=user.username,
        action="DELETE",
        resource_type="Camera",
        resource_id=camera_id
    )
    
    await db.commit()

async def mjpeg_generator(camera_id: str, redis_client):
    while True:
        try:
            frame_bytes = await redis_client.get(f"camera_frame:{camera_id}")
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # If no frame is available, yield a small blank frame or wait
                pass
        except Exception as e:
            print("Error getting frame from Redis:", e)
        await asyncio.sleep(0.05)

@router.get("/{camera_id}/stream")
async def get_camera_stream(camera_id: str):
    import redis.asyncio as redis
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    return StreamingResponse(mjpeg_generator(camera_id, redis_client), media_type="multipart/x-mixed-replace; boundary=frame")
