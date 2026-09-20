import sys
import pytest
from datetime import datetime, timezone

from app.models.tracker import Track, TrackState
from app.events.schema import EventType
from app.rules.fence import VirtualFenceRule, FenceState

def mock_track():
    return Track(
        track_id="trk-1",
        class_name="person",
        bbox=(0, 0, 10, 10),
        confidence=0.9,
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc),
        state=TrackState.TRACKED
    )

# A simple rectangular fence from (10,10) to (20,20)
FENCE_POLYGON = [(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)]

def test_debounce_inbound():
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    track = mock_track()
    state = FenceState()
    
    # 1. Outside
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "INBOUND", 2, track, (0.0, 0.0), state
    )
    assert evt is None
    assert state.is_inside is False
    assert state.consecutive_frames == 1
    assert state.confirmed_inside is False
    
    # 2. Moves Inside (frame 1 of inside) -> debounce is 2, so no event yet
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "INBOUND", 2, track, (15.0, 15.0), state
    )
    assert evt is None
    assert state.is_inside is True
    assert state.consecutive_frames == 1
    assert state.confirmed_inside is False
    
    # 3. Still Inside (frame 2 of inside) -> triggers event
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "INBOUND", 2, track, (15.0, 15.0), state
    )
    assert evt is not None
    assert evt.type == EventType.VIRTUAL_FENCE_INTRUSION
    assert evt.metadata["direction"] == "INBOUND"
    assert state.is_inside is True
    assert state.consecutive_frames == 2
    assert state.confirmed_inside is True
    
    # 4. Still Inside (frame 3) -> no new event
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "INBOUND", 2, track, (15.0, 15.0), state
    )
    assert evt is None


def test_debounce_outbound():
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    track = mock_track()
    # Start with it already confirmed inside
    state = FenceState(is_inside=True, consecutive_frames=5, confirmed_inside=True)
    
    # 1. Moves Outside (frame 1)
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "OUTBOUND", 2, track, (0.0, 0.0), state
    )
    assert evt is None
    assert state.is_inside is False
    
    # 2. Still Outside (frame 2) -> triggers
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "OUTBOUND", 2, track, (0.0, 0.0), state
    )
    assert evt is not None
    assert evt.metadata["direction"] == "OUTBOUND"
    assert state.confirmed_inside is False


def test_direction_filtering():
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    track = mock_track()
    state = FenceState()
    
    # 1. Start inside
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "OUTBOUND", 1, track, (15.0, 15.0), state
    )
    # Event should be None because we went from unconfirmed(outside) to inside, but filter is OUTBOUND
    assert evt is None
    assert state.confirmed_inside is True
    
    # 2. Move outside -> triggers OUTBOUND
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "OUTBOUND", 1, track, (0.0, 0.0), state
    )
    assert evt is not None
    assert evt.metadata["direction"] == "OUTBOUND"
    assert state.confirmed_inside is False


def test_any_direction():
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    track = mock_track()
    state = FenceState()
    
    # Inside triggers
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "ANY", 1, track, (15.0, 15.0), state
    )
    assert evt is not None
    assert evt.metadata["direction"] == "INBOUND"
    
    # Outside triggers
    evt, state = VirtualFenceRule.evaluate(
        "cam1", "zone1", FENCE_POLYGON, "ANY", 1, track, (0.0, 0.0), state
    )
    assert evt is not None
    assert evt.metadata["direction"] == "OUTBOUND"
