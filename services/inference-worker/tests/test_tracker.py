import pytest
import numpy as np
from datetime import datetime, timezone
from app.models.detector import Detection
from app.models.tracker import ByteTracker, TrackState, iou, draw_tracks


def make_det(bbox, conf=0.9):
    return Detection(
        class_name="person",
        confidence=conf,
        bbox=bbox,
        timestamp=datetime.now(timezone.utc)
    )

def test_iou():
    box1 = (0.0, 0.0, 10.0, 10.0)
    box2 = (0.0, 0.0, 10.0, 10.0)
    assert iou(box1, box2) == 1.0
    
    box3 = (10.0, 10.0, 20.0, 20.0)
    assert iou(box1, box3) == 0.0
    
    box4 = (5.0, 0.0, 15.0, 10.0)
    assert iou(box1, box4) == 1/3  # 50 / 150 = 1/3


def test_tracker_new_object():
    tracker = ByteTracker()
    dets = [make_det((10, 10, 20, 20))]
    
    tracks = tracker.update(dets)
    
    assert len(tracks) == 1
    assert tracks[0].state == TrackState.NEW
    assert tracks[0].hit_count == 1
    assert len(tracks[0].trajectory) == 1


def test_tracker_persistent_object():
    tracker = ByteTracker()
    
    # Frame 1
    tracks = tracker.update([make_det((10, 10, 20, 20))])
    assert tracks[0].state == TrackState.NEW
    track_id = tracks[0].track_id
    
    # Frame 2 (slight movement, high confidence)
    tracks = tracker.update([make_det((11, 11, 21, 21))])
    assert len(tracks) == 1
    assert tracks[0].track_id == track_id
    assert tracks[0].state == TrackState.TRACKED
    assert tracks[0].hit_count == 2
    assert len(tracks[0].trajectory) == 2


def test_tracker_multiple_objects():
    tracker = ByteTracker()
    
    dets = [
        make_det((10, 10, 20, 20)),
        make_det((100, 100, 120, 120))
    ]
    tracks = tracker.update(dets)
    assert len(tracks) == 2
    
    id1 = tracks[0].track_id
    id2 = tracks[1].track_id
    assert id1 != id2


def test_tracker_temporary_occlusion():
    tracker = ByteTracker(max_lost=3)
    
    # Frame 1
    tracker.update([make_det((10, 10, 20, 20))])
    
    # Frame 2 (no detections, object occluded)
    tracks_active = tracker.update([])
    assert len(tracks_active) == 0 # returns active only
    assert len(tracker.tracks) == 1
    assert tracker.tracks[0].state == TrackState.LOST
    assert tracker.tracks[0].lost_count == 1
    
    # Frame 3 (object returns)
    tracks_active = tracker.update([make_det((10, 10, 20, 20))])
    assert len(tracks_active) == 1
    assert tracks_active[0].state == TrackState.TRACKED
    assert tracks_active[0].lost_count == 0


def test_tracker_object_disappearance():
    tracker = ByteTracker(max_lost=2)
    
    tracker.update([make_det((10, 10, 20, 20))])
    
    # Lost 1
    tracker.update([])
    assert tracker.tracks[0].state == TrackState.LOST
    
    # Lost 2
    tracker.update([])
    assert tracker.tracks[0].state == TrackState.LOST
    
    # Lost 3 (exceeds max_lost = 2)
    tracker.update([])
    assert len(tracker.tracks) == 0 # REMOVED tracks are purged


def test_two_stage_matching_dlow():
    tracker = ByteTracker(high_thresh=0.6, track_thresh=0.4)
    
    # First frame, high confidence (NEW)
    tracks = tracker.update([make_det((10, 10, 20, 20), conf=0.9)])
    assert len(tracks) == 1
    
    # Second frame, high confidence (TRACKED)
    tracks = tracker.update([make_det((10, 10, 20, 20), conf=0.9)])
    assert tracks[0].state == TrackState.TRACKED

    # Third frame, same box but low confidence (D_low)
    tracks = tracker.update([make_det((10, 10, 20, 20), conf=0.5)])
    
    assert len(tracks) == 1
    assert tracks[0].state == TrackState.TRACKED
    assert tracks[0].confidence == 0.5


def test_draw_tracks():
    # cv2 is optional in the env, we mock it out or just ensure it runs
    import sys
    if 'cv2' not in sys.modules:
        pytest.skip("cv2 not installed")
        
    import cv2
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    tracker = ByteTracker()
    tracks = tracker.update([make_det((10, 10, 20, 20))])
    
    out_frame = draw_tracks(frame, tracks)
    assert out_frame is not None
