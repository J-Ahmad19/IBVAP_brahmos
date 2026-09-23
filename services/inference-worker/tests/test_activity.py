import datetime
from app.events.schema import EventType, Severity
from app.models.tracker import Track, TrackState
from app.models.behavior import BehaviorFeatures
from app.rules.activity import SuspiciousActivityRule

def test_rapid_approach():
    track = Track(
        track_id="t1",
        class_name="person",
        bbox=(0, 0, 10, 10),
        confidence=0.9,
        first_seen=datetime.datetime.now(datetime.timezone.utc),
        last_seen=datetime.datetime.now(datetime.timezone.utc)
    )
    
    features = BehaviorFeatures(
        centroid=(5.0, 5.0),
        foot_point=(5.0, 10.0),
        speed=15.0,
        direction=(1.0, 0.0),
        dwell_time=5.0,
        distance_to_fence=2.0,
        reentry_count=0
    )
    
    # Should trigger
    event = SuspiciousActivityRule.rapid_approach("cam1", track, features, speed_threshold=10.0, distance_threshold=5.0)
    assert event is not None
    assert event.type == EventType.SUSPICIOUS_MOVEMENT
    assert event.severity == Severity.HIGH
    assert event.metadata["rule"] == "rapid_approach"
    assert event.metadata["speed"] == 15.0
    
    # Should not trigger (speed too low)
    features.speed = 5.0
    event = SuspiciousActivityRule.rapid_approach("cam1", track, features, speed_threshold=10.0, distance_threshold=5.0)
    assert event is None

    # Should not trigger (distance too far)
    features.speed = 15.0
    features.distance_to_fence = 10.0
    event = SuspiciousActivityRule.rapid_approach("cam1", track, features, speed_threshold=10.0, distance_threshold=5.0)
    assert event is None

def test_restricted_after_hours():
    track = Track(
        track_id="t1",
        class_name="vehicle",
        bbox=(0, 0, 10, 10),
        confidence=0.9,
        first_seen=datetime.datetime.now(datetime.timezone.utc),
        last_seen=datetime.datetime.now(datetime.timezone.utc)
    )
    
    # Test spanning midnight (22:00 to 06:00)
    current_time = datetime.datetime(2023, 1, 1, 23, 0, 0, tzinfo=datetime.timezone.utc)
    event = SuspiciousActivityRule.restricted_after_hours("cam1", track, start_hour=22, end_hour=6, current_time=current_time)
    assert event is not None
    assert event.type == EventType.NIGHT_MOVEMENT
    assert event.metadata["rule"] == "restricted_after_hours"
    assert event.metadata["hour"] == 23
    
    # Test outside spanning midnight
    current_time = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    event = SuspiciousActivityRule.restricted_after_hours("cam1", track, start_hour=22, end_hour=6, current_time=current_time)
    assert event is None

    # Test same day (01:00 to 05:00)
    current_time = datetime.datetime(2023, 1, 1, 3, 0, 0, tzinfo=datetime.timezone.utc)
    event = SuspiciousActivityRule.restricted_after_hours("cam1", track, start_hour=1, end_hour=5, current_time=current_time)
    assert event is not None
    
    # Test same day outside
    current_time = datetime.datetime(2023, 1, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)
    event = SuspiciousActivityRule.restricted_after_hours("cam1", track, start_hour=1, end_hour=5, current_time=current_time)
    assert event is None

def test_repeated_reentry():
    track = Track(
        track_id="t1",
        class_name="person",
        bbox=(0, 0, 10, 10),
        confidence=0.9,
        first_seen=datetime.datetime.now(datetime.timezone.utc),
        last_seen=datetime.datetime.now(datetime.timezone.utc)
    )
    
    features = BehaviorFeatures(
        centroid=(5.0, 5.0),
        foot_point=(5.0, 10.0),
        speed=2.0,
        direction=(1.0, 0.0),
        dwell_time=5.0,
        reentry_count=3
    )
    
    # Should trigger
    event = SuspiciousActivityRule.repeated_reentry("cam1", track, features, max_reentry_count=2)
    assert event is not None
    assert event.type == EventType.SUSPICIOUS_MOVEMENT
    assert event.metadata["rule"] == "repeated_reentry"
    assert event.metadata["reentry_count"] == 3
    
    # Should not trigger
    event = SuspiciousActivityRule.repeated_reentry("cam1", track, features, max_reentry_count=5)
    assert event is None

def test_prolonged_stationary_activity():
    track = Track(
        track_id="t1",
        class_name="person",
        bbox=(0, 0, 10, 10),
        confidence=0.9,
        first_seen=datetime.datetime.now(datetime.timezone.utc),
        last_seen=datetime.datetime.now(datetime.timezone.utc)
    )
    
    features = BehaviorFeatures(
        centroid=(5.0, 5.0),
        foot_point=(5.0, 10.0),
        speed=0.2,
        direction=(1.0, 0.0),
        dwell_time=120.0,
        reentry_count=0
    )
    
    # Should trigger
    event = SuspiciousActivityRule.prolonged_stationary_activity("cam1", track, features, dwell_threshold=60.0, speed_threshold=0.5)
    assert event is not None
    assert event.type == EventType.SUSPICIOUS_MOVEMENT
    assert event.metadata["rule"] == "prolonged_stationary_activity"
    assert event.metadata["dwell_time"] == 120.0
    
    # Should not trigger (dwell too short)
    features.dwell_time = 30.0
    event = SuspiciousActivityRule.prolonged_stationary_activity("cam1", track, features, dwell_threshold=60.0, speed_threshold=0.5)
    assert event is None
    
    # Should not trigger (speed too high)
    features.dwell_time = 120.0
    features.speed = 1.5
    event = SuspiciousActivityRule.prolonged_stationary_activity("cam1", track, features, dwell_threshold=60.0, speed_threshold=0.5)
    assert event is None
