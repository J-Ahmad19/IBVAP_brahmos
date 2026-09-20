import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.events.schema import Event, EventType, Severity, EventFactory, EventValidator

def test_valid_event():
    """Test creating a valid event using the factory and schema directly."""
    # Using Schema
    event1 = Event(
        type=EventType.LOITERING,
        camera_id="cam-1",
        confidence=0.95,
        severity=Severity.MEDIUM,
        metadata={"dwell_time": 120}
    )
    assert event1.type == EventType.LOITERING
    assert event1.camera_id == "cam-1"
    assert event1.confidence == 0.95
    assert event1.severity == Severity.MEDIUM
    assert event1.event_id is not None
    assert event1.timestamp is not None
    assert event1.timestamp.tzinfo is not None

    # Using Factory
    event2 = EventFactory.create(
        event_type=EventType.ANPR_MATCH,
        camera_id="cam-2",
        confidence=0.88,
        severity=Severity.HIGH,
        track_id="trk-1"
    )
    assert event2.type == EventType.ANPR_MATCH
    assert event2.camera_id == "cam-2"
    assert event2.severity == Severity.HIGH
    assert event2.track_id == "trk-1"


def test_invalid_event():
    """Test entirely invalid payloads via EventValidator."""
    with pytest.raises(ValidationError):
        EventValidator.validate({"random_field": "data"})


def test_missing_required_field():
    """Test missing camera_id and type."""
    with pytest.raises(ValidationError) as exc:
        Event(type=EventType.LOITERING) # missing camera_id
    assert "camera_id" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        Event(camera_id="cam-1") # missing type
    assert "type" in str(exc.value)


def test_invalid_confidence():
    """Test confidence bounds (must be between 0.0 and 1.0)."""
    with pytest.raises(ValidationError) as exc:
        Event(type=EventType.LOITERING, camera_id="cam-1", confidence=1.5)
    assert "confidence" in str(exc.value)
    
    with pytest.raises(ValidationError) as exc:
        Event(type=EventType.LOITERING, camera_id="cam-1", confidence=-0.1)
    assert "confidence" in str(exc.value)


def test_invalid_severity():
    """Test an invalid severity enum string."""
    with pytest.raises(ValidationError) as exc:
        EventValidator.validate({
            "type": "LOITERING",
            "camera_id": "cam-1",
            "severity": "SUPER_HIGH"
        })
    assert "severity" in str(exc.value)


def test_invalid_event_type():
    """Test an invalid event type enum string."""
    with pytest.raises(ValidationError) as exc:
        EventValidator.validate({
            "type": "UNKNOWN_EVENT_THAT_IS_NOT_ALLOWED",
            "camera_id": "cam-1"
        })
    assert "type" in str(exc.value)


def test_naive_timestamp():
    """Test that a naive timestamp raises a validation error."""
    with pytest.raises(ValidationError) as exc:
        Event(
            type=EventType.LOITERING,
            camera_id="cam-1",
            timestamp=datetime.now() # Naive datetime
        )
    assert "timezone" in str(exc.value).lower()
