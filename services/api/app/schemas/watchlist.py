from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class WatchlistEntryBase(BaseModel):
    type: str  # 'FACE' or 'PLATE'
    label: str
    reference: Optional[str] = None
    enabled: bool = True
    threshold: Optional[float] = None

class WatchlistEntryCreate(WatchlistEntryBase):
    pass

class WatchlistEntryUpdate(BaseModel):
    label: Optional[str] = None
    reference: Optional[str] = None
    enabled: Optional[bool] = None
    threshold: Optional[float] = None

class WatchlistEntry(WatchlistEntryBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FaceWatchlistResponse(WatchlistEntry):
    """
    Response model for face watchlist entries.
    Explicitly does not contain the raw embedding vector.
    """
    pass
