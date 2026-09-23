from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from typing import List

try:
    from app.api.dependencies import get_db
except ImportError:
    async def get_db():
        yield None
from app.db.models import WatchlistEntry as DBWatchlistEntry
from app.schemas.watchlist import WatchlistEntry, WatchlistEntryCreate
from app.api.auth import User, get_admin
from app.api.audit import log_audit_event

router = APIRouter()

@router.post("", response_model=WatchlistEntry, status_code=status.HTTP_201_CREATED)
async def create_plate_entry(
    entry: WatchlistEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_admin)
):
    """
    Enroll a plate into the watchlist.
    """
    if entry.type != "PLATE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entry type must be PLATE"
        )
        
    # Check if plate already exists
    stmt = select(DBWatchlistEntry).where(
        DBWatchlistEntry.type == "PLATE",
        DBWatchlistEntry.label == entry.label
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plate already exists in watchlist"
        )

    db_entry = DBWatchlistEntry(
        type="PLATE",
        label=entry.label,
        reference=entry.reference,
        enabled=entry.enabled,
        threshold=entry.threshold
    )
    db.add(db_entry)
    
    await log_audit_event(
        db=db,
        actor=user.username,
        action="CREATE",
        resource_type="PlateWatchlist",
        resource_id=entry.label,
        metadata={"label": entry.label}
    )
    
    await db.commit()
    await db.refresh(db_entry)
    
    return db_entry

@router.get("", response_model=List[WatchlistEntry])
async def get_plate_entries(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all enrolled plates.
    """
    stmt = select(DBWatchlistEntry).where(DBWatchlistEntry.type == "PLATE").offset(skip).limit(limit)
    result = await db.execute(stmt)
    entries = result.scalars().all()
    return entries

@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plate_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_admin)
):
    """
    Remove a plate from the watchlist.
    """
    stmt = select(DBWatchlistEntry).where(
        DBWatchlistEntry.id == entry_id,
        DBWatchlistEntry.type == "PLATE"
    )
    result = await db.execute(stmt)
    db_entry = result.scalars().first()
    
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plate entry not found"
        )
        
    await db.delete(db_entry)
    
    await log_audit_event(
        db=db,
        actor=user.username,
        action="DELETE",
        resource_type="PlateWatchlist",
        resource_id=str(entry_id)
    )
    
    await db.commit()
