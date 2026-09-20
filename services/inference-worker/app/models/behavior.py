import math
import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.tracker import Track

try:
    import cv2
except ImportError:
    cv2 = None


@dataclass
class BehaviorFeatures:
    centroid: Tuple[float, float]
    foot_point: Tuple[float, float]
    speed: float  # pixels per frame in bounded history
    direction: Tuple[float, float]  # Normalized vector (dx, dy)
    dwell_time: float  # Seconds
    distance_to_fence: Optional[float] = None
    reentry_count: int = 0


class BehaviorFeatureExtractor:
    """
    Extracts trajectory and geometric behavior features from a track.
    Does NOT use deep-learning behavior models (as per Phase 6A rules).
    Features are passed to the downstream rule engine.
    """
    
    def extract(self, track: Track, fence_polygon: Optional[List[Tuple[float, float]]] = None) -> BehaviorFeatures:
        bbox = track.bbox
        
        # 1. Centroid & Foot Point
        centroid = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
        foot_point = ((bbox[0] + bbox[2]) / 2.0, bbox[3])
        
        # 2. Dwell Time
        now = track.last_seen or datetime.now(timezone.utc)
        dwell_time = (now - track.first_seen).total_seconds()
        if dwell_time < 0:
            dwell_time = 0.0

        # 3. Speed & Direction (Using bounded trajectory history)
        speed = 0.0
        direction = (0.0, 0.0)
        traj = list(track.trajectory)
        
        if len(traj) > 1:
            p_start = traj[0]
            p_end = traj[-1]
            dx = p_end[0] - p_start[0]
            dy = p_end[1] - p_start[1]
            distance = math.sqrt(dx**2 + dy**2)
            
            speed = distance / len(traj)  # simple proxy: pixels per frame
            
            if distance > 0:
                direction = (dx / distance, dy / distance)

        # 4. Fence Operations
        distance_to_fence = None
        reentry_count = 0
        
        if fence_polygon is not None and cv2 is not None and len(fence_polygon) >= 3:
            poly_np = np.array(fence_polygon, dtype=np.int32)
            
            # Distance from foot point to fence edge
            # cv2.pointPolygonTest with measureDist=True returns positive if inside, negative if outside, 0 on edge
            dist = cv2.pointPolygonTest(poly_np, (float(foot_point[0]), float(foot_point[1])), True)
            distance_to_fence = abs(dist)
            
            # Re-entry count
            # Count False -> True transitions (Outside -> Inside)
            is_inside = False
            entries = 0
            
            for pt in traj:
                res = cv2.pointPolygonTest(poly_np, (float(pt[0]), float(pt[1])), False)
                curr_inside = res >= 0
                if curr_inside and not is_inside:
                    entries += 1
                is_inside = curr_inside
                
            reentry_count = entries

        return BehaviorFeatures(
            centroid=centroid,
            foot_point=foot_point,
            speed=speed,
            direction=direction,
            dwell_time=dwell_time,
            distance_to_fence=distance_to_fence,
            reentry_count=reentry_count
        )
