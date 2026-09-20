from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class CameraBase(BaseModel):
    name: str
    source_type: str
    source_uri: str
    location: Optional[str] = None
    zone: Optional[str] = None
    priority: int = 1
    enabled: bool = True

class CameraCreate(CameraBase):
    id: str

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    source_type: Optional[str] = None
    source_uri: Optional[str] = None
    location: Optional[str] = None
    zone: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None

class Camera(CameraBase):
    id: str
    status: str
    last_frame_ts: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
