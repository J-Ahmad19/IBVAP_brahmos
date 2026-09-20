from pydantic import BaseModel
from typing import Dict

class ComponentHealth(BaseModel):
    status: str
    details: str = ""

class SystemHealth(BaseModel):
    status: str
    version: str = "1.0.0"
    components: Dict[str, ComponentHealth]
