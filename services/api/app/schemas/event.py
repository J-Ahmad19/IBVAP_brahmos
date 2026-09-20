import os
import sys
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# Hack to import from the inference-worker service without duplicating the schema.
# In a true microservice environment, this would be a shared pip package.
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))
try:
    from services.inference_worker.app.events.schema import Event, EventType, Severity
except ImportError:
    # Handle hyphens in directory name
    sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../services/inference-worker"))
    from app.events.schema import Event, EventType, Severity

class EventResponse(BaseModel):
    """API Response for Events. Can wrap the canonical event or return a list."""
    data: Event

class EventListResponse(BaseModel):
    data: List[Event]
    total: int
    page: int
    size: int
