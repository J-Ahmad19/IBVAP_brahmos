import sys
import pytest
from datetime import datetime, timezone, timedelta

from app.models.tracker import Track, TrackState
from app.events.schema import EventType
from app.rules.loitering import LoiteringRule, LoiteringState

def mock_track(last_seen_time):
    return Track(
        track_id="trk-1",
        class_name="person",
        bbox=(0, 0, 10, 10),
        confidence=0.9,
        first_seen=last_seen_time,
        last_seen=last_seen_time,
        state=TrackState.TRACKED
    )

# A simple rectangular ROI from (10,10) to (20,20)
ROI_POLYGON = [(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)]

def test_loitering_triggers_after_threshold():
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    start_time = datetime.now(timezone.utc)
    state = LoiteringState()
    
    # 1. Enters ROI at T=0
    track_t0 = mock_track(start_time)
    evt, state = LoiteringRule.evaluate(
        "cam1", "zone1", ROI_POLYGON, 5.0, 10.0, track_t0, (15.0, 15.0), state
    )
    assert evt is None
    assert state.is_inside is True
    assert state.first_entered_at == start_time
    
    # 2. Inside ROI at T=3 (below threshold)
    track_t3 = mock_track(start_time + timedelta(seconds=3))
    evt, state = LoiteringRule.evaluate(
        "cam1", "zone1", ROI_POLYGON, 5.0, 10.0, track_t3, (15.0, 15.0), state
    )
    assert evt is None
    assert state.is_inside is True
    
    # 3. Inside ROI at T=6 (exceeds threshold)
    track_t6 = mock_track(start_time + timedelta(seconds=6))
    evt, state = LoiteringRule.evaluate(
        "cam1", "zone1", ROI_POLYGON, 5.0, 10.0, track_t6, (15.0, 15.0), state
    )
    assert evt is not None
    assert evt.type == EventType.LOITERING
    assert evt.metadata["dwell_time"] == 6.0
    assert state.last_event_time == track_t6.last_seen


def test_loitering_cooldown():
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    start_time = datetime.now(timezone.utc)
    state = LoiteringState()
    
    # 1. T=0 Enters
    track = mock_track(start_time)
    evt, state = LoiteringRule.evaluate("cam1", "z", ROI_POLYGON, 5.0, 10.0, track, (15.0, 15.0), state)
    
    # 2. T=6 Triggers (threshold=5)
    track = mock_track(start_time + timedelta(seconds=6))
    evt, state = LoiteringRule.evaluate("cam1", "z", ROI_POLYGON, 5.0, 10.0, track, (15.0, 15.0), state)
    assert evt is not None
    
    # 3. T=9 Still inside (time since last event = 3 < cooldown 10)
    track = mock_track(start_time + timedelta(seconds=9))
    evt, state = LoiteringRule.evaluate("cam1", "z", ROI_POLYGON, 5.0, 10.0, track, (15.0, 15.0), state)
    assert evt is None  # Cooldown active
    
    # 4. T=17 Still inside (time since last event = 11 >= cooldown 10)
    track = mock_track(start_time + timedelta(seconds=17))
    evt, state = LoiteringRule.evaluate("cam1", "z", ROI_POLYGON, 5.0, 10.0, track, (15.0, 15.0), state)
    assert evt is not None  # Cooldown passed, triggers again
    assert evt.metadata["dwell_time"] == 17.0


def test_loitering_reset_on_exit():
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    start_time = datetime.now(timezone.utc)
    state = LoiteringState()
    
    # 1. T=0 Enters
    track = mock_track(start_time)
    evt, state = LoiteringRule.evaluate("cam1", "z", ROI_POLYGON, 5.0, 10.0, track, (15.0, 15.0), state)
    
    # 2. T=3 Exits ROI
    track = mock_track(start_time + timedelta(seconds=3))
    evt, state = LoiteringRule.evaluate("cam1", "z", ROI_POLYGON, 5.0, 10.0, track, (0.0, 0.0), state)
    assert evt is None
    assert state.is_inside is False
    assert state.first_entered_at is None
    
    # 3. T=4 Re-enters ROI
    track = mock_track(start_time + timedelta(seconds=4))
    evt, state = LoiteringRule.evaluate("cam1", "z", ROI_POLYGON, 5.0, 10.0, track, (15.0, 15.0), state)
    assert state.first_entered_at == track.last_seen
    
    # 4. T=8 Inside (dwell = 4 < threshold 5)
    track = mock_track(start_time + timedelta(seconds=8))
    evt, state = LoiteringRule.evaluate("cam1", "z", ROI_POLYGON, 5.0, 10.0, track, (15.0, 15.0), state)
    assert evt is None  # If it hadn't reset, total time would be 8, which is > 5. But since it reset, dwell is 4.
