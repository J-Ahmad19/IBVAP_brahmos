import time
import uuid
import logging
from enum import Enum
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timezone

from app.models.detector import Detection

try:
    import cv2
except ImportError:
    cv2 = None

logger = logging.getLogger(__name__)

class TrackState(Enum):
    NEW = 1
    TRACKED = 2
    LOST = 3
    REMOVED = 4

@dataclass
class Track:
    track_id: str
    class_name: str
    bbox: Tuple[float, float, float, float]
    confidence: float
    first_seen: datetime
    last_seen: datetime
    trajectory: deque = field(default_factory=lambda: deque(maxlen=50))
    state: TrackState = TrackState.NEW
    lost_count: int = 0
    hit_count: int = 1


def iou(box1: Tuple[float, float, float, float], box2: Tuple[float, float, float, float]) -> float:
    """Calculate Intersection over Union (IoU) of two bounding boxes (x_min, y_min, x_max, y_max)."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    if inter_area == 0:
        return 0.0

    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area
    
    if union_area == 0:
        return 0.0
        
    return inter_area / union_area


class ByteTracker:
    """
    ByteTrack-style Tracker (Pure IoU without Kalman Filter for simplicity in prototype).
    Implements two-stage matching: D_high matches first, then D_low matches leftovers.
    """
    def __init__(self, 
                 track_thresh: float = 0.5, 
                 high_thresh: float = 0.6, 
                 match_thresh: float = 0.8, 
                 max_lost: int = 30):
        self.track_thresh = track_thresh
        self.high_thresh = high_thresh
        self.match_thresh = match_thresh # distance threshold (1 - iou)
        self.max_lost = max_lost
        
        self.tracks: List[Track] = []

    def update(self, detections: List[Detection]) -> List[Track]:
        """
        Updates the tracker with new detections.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Split detections into High and Low
        d_high = [d for d in detections if d.confidence >= self.high_thresh]
        d_low = [d for d in detections if self.track_thresh <= d.confidence < self.high_thresh]
        
        # Split active tracks
        active_tracks = [t for t in self.tracks if t.state in (TrackState.TRACKED, TrackState.NEW)]
        lost_tracks = [t for t in self.tracks if t.state == TrackState.LOST]
        
        pool = active_tracks + lost_tracks

        # Stage 1: Match D_high with pool
        matched_tracks_1, unmatched_tracks_1, unmatched_dets_1 = self._match(pool, d_high)

        # Stage 2: Match D_low with unmatched tracks from Stage 1 (only TRACKED, not NEW or LOST)
        # ByteTrack usually only matches low conf to existing confident tracks to avoid false positives
        unmatched_active_tracks = [t for t in unmatched_tracks_1 if t.state == TrackState.TRACKED]
        matched_tracks_2, unmatched_tracks_2, _ = self._match(unmatched_active_tracks, d_low)

        # Update matched tracks
        all_matches = matched_tracks_1 + matched_tracks_2
        for track, det in all_matches:
            self._update_track(track, det, now)

        # Handle unmatched detections (D_high only become new tracks)
        new_tracks = []
        for det in unmatched_dets_1:
            new_track = Track(
                track_id=str(uuid.uuid4())[:8], # Short ID for visualization
                class_name=det.class_name,
                bbox=det.bbox,
                confidence=det.confidence,
                first_seen=now,
                last_seen=now,
                state=TrackState.NEW
            )
            new_track.trajectory.append(self._get_center(det.bbox))
            new_tracks.append(new_track)
            
        # Handle unmatched tracks (become LOST)
        lost_tracks_pool = [t for t in unmatched_tracks_1 if t.state != TrackState.TRACKED] + unmatched_tracks_2
        for track in lost_tracks_pool:
            if track.state != TrackState.LOST:
                track.state = TrackState.LOST
                track.lost_count = 1
            else:
                track.lost_count += 1

        # Remove long-lost tracks
        active_and_lost = []
        for t in self.tracks + new_tracks:
            if t.state == TrackState.LOST and t.lost_count > self.max_lost:
                t.state = TrackState.REMOVED
            if t.state != TrackState.REMOVED:
                active_and_lost.append(t)
                
        # To avoid duplicates if we just add new_tracks to self.tracks naively, 
        # we rebuild the list
        self.tracks = active_and_lost
        
        # Return only currently tracked or newly instantiated objects
        return [t for t in self.tracks if t.state in (TrackState.TRACKED, TrackState.NEW)]

    def _match(self, tracks: List[Track], detections: List[Detection]) -> Tuple[List[Tuple[Track, Detection]], List[Track], List[Detection]]:
        if not tracks or not detections:
            return [], tracks, detections
            
        # Build IoU cost matrix
        cost_matrix = []
        for t in tracks:
            row = []
            for d in detections:
                iou_val = iou(t.bbox, d.bbox)
                cost = 1.0 - iou_val
                row.append(cost)
            cost_matrix.append(row)
            
        # Greedy matching (scipy.optimize.linear_sum_assignment could be used for Hungarian, 
        # but greedy is fine for a lightweight prototype and doesn't require scipy)
        matched_tracks = []
        unmatched_tracks = set(range(len(tracks)))
        unmatched_dets = set(range(len(detections)))
        
        # Sort all costs
        flat_costs = []
        for i, row in enumerate(cost_matrix):
            for j, cost in enumerate(row):
                flat_costs.append((cost, i, j))
                
        flat_costs.sort(key=lambda x: x[0])
        
        for cost, i, j in flat_costs:
            if i in unmatched_tracks and j in unmatched_dets:
                if cost > self.match_thresh:
                    continue # Ignore matches that are too far apart
                matched_tracks.append((tracks[i], detections[j]))
                unmatched_tracks.remove(i)
                unmatched_dets.remove(j)
                
        remaining_tracks = [tracks[i] for i in unmatched_tracks]
        remaining_dets = [detections[j] for j in unmatched_dets]
        
        return matched_tracks, remaining_tracks, remaining_dets

    def _update_track(self, track: Track, det: Detection, now: datetime):
        track.bbox = det.bbox
        track.confidence = det.confidence
        track.last_seen = now
        track.hit_count += 1
        track.lost_count = 0
        if track.state in (TrackState.NEW, TrackState.LOST):
            track.state = TrackState.TRACKED
        track.trajectory.append(self._get_center(det.bbox))

    def _get_center(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def draw_tracks(frame: Any, tracks: List[Track]) -> Any:
    """Helper to draw bounding boxes and trajectories onto an OpenCV frame."""
    if cv2 is None or frame is None:
        return frame
        
    for t in tracks:
        # Draw bounding box
        x1, y1, x2, y2 = [int(v) for v in t.bbox]
        color = (0, 255, 0) if t.state == TrackState.TRACKED else (0, 165, 255)
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw label
        label = f"{t.class_name} #{t.track_id} {t.confidence:.2f}"
        cv2.putText(frame, label, (x1, max(0, y1 - 10)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                    
        # Draw trajectory
        if len(t.trajectory) > 1:
            pts = list(t.trajectory)
            for i in range(1, len(pts)):
                pt1 = (int(pts[i-1][0]), int(pts[i-1][1]))
                pt2 = (int(pts[i][0]), int(pts[i][1]))
                cv2.line(frame, pt1, pt2, (255, 0, 0), 2)
                
    return frame
