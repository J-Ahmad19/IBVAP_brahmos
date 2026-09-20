from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any

class FenceBase(BaseModel):
    camera_id: str
    name: str
    polygon: Dict[str, Any]  # GeoJSON style or simple coordinate list
    direction: str = "BOTH"
    debounce_frames: int = 3
    enabled: bool = True

class FenceCreate(FenceBase):
    pass

class FenceUpdate(BaseModel):
    name: Optional[str] = None
    polygon: Optional[Dict[str, Any]] = None
    direction: Optional[str] = None
    debounce_frames: Optional[int] = None
    enabled: Optional[bool] = None

class Fence(FenceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
