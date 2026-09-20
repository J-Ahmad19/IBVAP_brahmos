import pytest
import math
from datetime import datetime, timezone, timedelta
from collections import deque

from app.models.tracker import Track, TrackState
from app.models.behavior import BehaviorFeatureExtractor, BehaviorFeatures

def create_mock_track(trajectory_points, first_seen_offset_sec=10):
    now = datetime.now(timezone.utc)
    first_seen = now - timedelta(seconds=first_seen_offset_sec)
    
    # Assume bbox matches the last trajectory point (for centroid/foot computation)
    # Give a 20x20 box around it
    last_pt = trajectory_points[-1]
    bbox = (last_pt[0] - 10, last_pt[1] - 20, last_pt[0] + 10, last_pt[1])
    
    track = Track(
        track_id="test-1",
        class_name="person",
        bbox=bbox,
        confidence=0.9,
        first_seen=first_seen,
        last_seen=now,
        trajectory=deque(trajectory_points, maxlen=50),
        state=TrackState.TRACKED
    )
    return track


def test_basic_features():
    extractor = BehaviorFeatureExtractor()
    
    # Trajectory moves from (0,0) to (30,40) over 5 points. Total distance 50.
    points = [(0,0), (7.5, 10), (15, 20), (22.5, 30), (30, 40)]
    track = create_mock_track(points, 5.0)
    
    feats = extractor.extract(track)
    
    # Centroid: bbox is (20, 20, 40, 40). Center is (30, 30)
    # bbox was: (30-10, 40-20, 30+10, 40) => (20, 20, 40, 40)
    assert feats.centroid == (30.0, 30.0)
    # Foot point: (30, 40)
    assert feats.foot_point == (30.0, 40.0)
    
    # Speed: dist = 50. len = 5. Speed = 10 px/frame
    assert feats.speed == 10.0
    
    # Direction: normalized vector from (0,0) to (30,40). distance = 50
    # dx=30, dy=40 -> 30/50, 40/50 = 0.6, 0.8
    assert math.isclose(feats.direction[0], 0.6)
    assert math.isclose(feats.direction[1], 0.8)
    
    # Dwell time
    assert math.isclose(feats.dwell_time, 5.0, abs_tol=0.01)


def test_fence_distance():
    extractor = BehaviorFeatureExtractor()
    
    # Object at (50, 50)
    points = [(50, 50)]
    track = create_mock_track(points)
    
    # Fence is a simple rectangle from (100, 0) to (200, 100)
    fence = [(100, 0), (200, 0), (200, 100), (100, 100)]
    
    # OpenCV required for this
    import sys
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    feats = extractor.extract(track, fence_polygon=fence)
    
    # Foot point is (50, 50). Distance to left edge x=100 is 50.
    assert feats.distance_to_fence is not None
    assert math.isclose(feats.distance_to_fence, 50.0, abs_tol=1.0)


def test_reentry_count():
    extractor = BehaviorFeatureExtractor()
    
    # Trajectory moves in, out, in
    # y is constant 50. x moves: 20 (out), 150 (in), 20 (out), 150 (in)
    points = [(20, 50), (150, 50), (20, 50), (150, 50)]
    track = create_mock_track(points)
    
    # Fence x from 100 to 200
    fence = [(100, 0), (200, 0), (200, 100), (100, 100)]
    
    import sys
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    feats = extractor.extract(track, fence_polygon=fence)
    
    assert feats.reentry_count == 2


def test_stationary_object():
    extractor = BehaviorFeatureExtractor()
    
    points = [(10, 10), (10, 10)]
    track = create_mock_track(points)
    feats = extractor.extract(track)
    
    assert feats.speed == 0.0
    assert feats.direction == (0.0, 0.0)
