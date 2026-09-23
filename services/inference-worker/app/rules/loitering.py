import numpy as np
from typing import Tuple, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone

from app.events.schema import Event, EventType, Severity, EventFactory
from app.models.tracker import Track

try:
    import cv2
except ImportError:
    cv2 = None

@dataclass
class LoiteringState:
    is_inside: bool = False
    first_entered_at: Optional[datetime] = None
    last_event_time: Optional[datetime] = None


class VirtualLoiteringRule:
    """
    Evaluates whether an object has been loitering inside an ROI for too long.
    Stateless evaluator: takes previous state and returns new state.
    """
    
    @staticmethod
    def evaluate(
        camera_id: str,
        zone_name: str,
        polygon: List[Tuple[float, float]],
        dwell_threshold: float,
        cooldown: float,
        track: Track,
        foot_point: Tuple[float, float],
        prev_state: Optional[LoiteringState] = None
    ) -> Tuple[Optional[Event], LoiteringState]:
        
        if cv2 is None:
            raise ImportError("OpenCV required for pointPolygonTest")
            
        if prev_state is None:
            prev_state = LoiteringState()
            
        poly_np = np.array(polygon, dtype=np.int32)
        res = cv2.pointPolygonTest(poly_np, (float(foot_point[0]), float(foot_point[1])), False)
        current_inside = (res >= 0)
        
        new_state = LoiteringState(
            is_inside=current_inside,
            first_entered_at=prev_state.first_entered_at,
            last_event_time=prev_state.last_event_time
        )
        
        event = None
        now = track.last_seen or datetime.now(timezone.utc)
        
        if current_inside:
            # Transition: Outside -> Inside
            if not prev_state.is_inside:
                new_state.first_entered_at = now
                new_state.last_event_time = None
                
            # Evaluate Dwell Time
            if new_state.first_entered_at is not None:
                dwell_time = (now - new_state.first_entered_at).total_seconds()
                
                if dwell_time >= dwell_threshold:
                    # Check Cooldown
                    time_since_last_event = float('inf')
                    if new_state.last_event_time is not None:
                        time_since_last_event = (now - new_state.last_event_time).total_seconds()
                        
                    if time_since_last_event >= cooldown:
                        # Generate LOITERING Event
                        event = EventFactory.create(
                            event_type=EventType.LOITERING,
                            camera_id=camera_id,
                            severity=Severity.MEDIUM,
                            track_id=track.track_id,
                            confidence=track.confidence,
                            metadata={
                                "zone": zone_name,
                                "dwell_time": round(dwell_time, 2),
                                "class_name": track.class_name
                            }
                        )
                        new_state.last_event_time = now
                        
        else:
            # Transition: Inside -> Outside (Reset)
            new_state.first_entered_at = None
            new_state.last_event_time = None
            
        return event, new_state


class LoiteringRule:
    """Wrapper around VirtualLoiteringRule to store state and handle evaluate(camera_id, track, features)."""
    def __init__(self):
        self.states = {}
        # Mock polygon for testing
        self.polygon = [(0, 0), (1280, 0), (1280, 720), (0, 720)]
        self.dwell_threshold = 10.0
        self.cooldown = 30.0
        
    def evaluate(self, camera_id: str, track: Track, features: Any) -> Optional[Event]:
        state_key = f"{camera_id}_{track.track_id}"
        prev_state = self.states.get(state_key)
        
        foot_point = features.foot_point if features else ((track.bbox[0] + track.bbox[2])/2, track.bbox[3])
        
        event, new_state = VirtualLoiteringRule.evaluate(
            camera_id=camera_id,
            zone_name="mock_zone",
            polygon=self.polygon,
            dwell_threshold=self.dwell_threshold,
            cooldown=self.cooldown,
            track=track,
            foot_point=foot_point,
            prev_state=prev_state
        )
        
        self.states[state_key] = new_state
        return event
