from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

try:
    from app.api.dependencies import get_db
except ImportError:
    async def get_db():
        yield None

from app.db.models import Fence as DBFence
from app.schemas.fence import Fence, FenceCreate, FenceUpdate
from app.api.auth import User, get_admin
from app.api.audit import log_audit_event

router = APIRouter()

@router.get("/{camera_id}", response_model=List[Fence])
async def list_fences_for_camera(camera_id: str, db: AsyncSession = Depends(get_db)):
    if not db:
        return []
    stmt = select(DBFence).where(DBFence.camera_id == camera_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=Fence, status_code=201)
async def create_fence(
    fence: FenceCreate, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_admin)
):
    if not db:
        return None
    db_fence = DBFence(**fence.model_dump())
    db.add(db_fence)
    
    await log_audit_event(
        db=db,
        actor=user.username,
        action="CREATE",
        resource_type="Fence",
        resource_id=f"camera_{fence.camera_id}",
        metadata=fence.model_dump()
    )
    
    await db.commit()
    await db.refresh(db_fence)
    return db_fence

@router.put("/{fence_id}", response_model=Fence)
async def update_fence(
    fence_id: int, 
    fence_update: FenceUpdate, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_admin)
):
    if not db:
        return None
    stmt = select(DBFence).where(DBFence.id == fence_id)
    result = await db.execute(stmt)
    db_fence = result.scalars().first()
    if not db_fence:
        raise HTTPException(status_code=404, detail="Fence not found")
        
    update_data = fence_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_fence, key, value)
        
    await log_audit_event(
        db=db,
        actor=user.username,
        action="UPDATE",
        resource_type="Fence",
        resource_id=str(fence_id),
        metadata=update_data
    )
        
    await db.commit()
    await db.refresh(db_fence)
    return db_fence

@router.delete("/{fence_id}", status_code=204)
async def delete_fence(
    fence_id: int, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_admin)
):
    if not db:
        return
    stmt = select(DBFence).where(DBFence.id == fence_id)
    result = await db.execute(stmt)
    db_fence = result.scalars().first()
    if not db_fence:
        raise HTTPException(status_code=404, detail="Fence not found")
        
    await db.delete(db_fence)
    
    await log_audit_event(
        db=db,
        actor=user.username,
        action="DELETE",
        resource_type="Fence",
        resource_id=str(fence_id)
    )
    
    await db.commit()
