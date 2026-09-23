import uuid
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    VIRTUAL_FENCE_INTRUSION = "VIRTUAL_FENCE_INTRUSION"
    LOITERING = "LOITERING"
    SUSPICIOUS_MOVEMENT = "SUSPICIOUS_MOVEMENT"
    NIGHT_MOVEMENT = "NIGHT_MOVEMENT"
    UNCLASSIFIED_MOVEMENT = "UNCLASSIFIED_MOVEMENT"
    ANPR_MATCH = "ANPR_MATCH"
    FACE_MATCH = "FACE_MATCH"


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Event(BaseModel):
    """
    Canonical Event Schema for IBVAP.
    Every downstream component MUST consume this schema.
    No module-specific JSON structures are allowed.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    camera_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    track_id: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    severity: Severity = Field(default=Severity.INFO)
    status: str = Field(default="NEW")
    media_ref: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('timestamp')
    @classmethod
    def ensure_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware")
        return v


class EventValidator:
    """Utility to validate raw dictionaries into strict Event schemas."""
    
    @staticmethod
    def validate(data: dict) -> Event:
        """Parses and validates a dictionary into an Event object. Raises ValidationError on failure."""
        return Event(**data)


class EventFactory:
    """Factory to simplify event creation for different modules."""
    
    @staticmethod
    def create(
        event_type: EventType,
        camera_id: str,
        severity: Severity = Severity.INFO,
        track_id: Optional[str] = None,
        confidence: Optional[float] = None,
        media_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Event:
        return Event(
            type=event_type,
            camera_id=camera_id,
            severity=severity,
            track_id=track_id,
            confidence=confidence,
            media_ref=media_ref,
            metadata=metadata or {}
        )
