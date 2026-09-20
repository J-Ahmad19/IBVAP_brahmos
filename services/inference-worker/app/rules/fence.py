import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass

from app.events.schema import Event, EventType, Severity, EventFactory
from app.models.tracker import Track

try:
    import cv2
except ImportError:
    cv2 = None


@dataclass
class FenceState:
    is_inside: bool = False
    consecutive_frames: int = 0
    confirmed_inside: bool = False


class VirtualFenceRule:
    """
    Evaluates a single Virtual Fence against a tracked object.
    Operates statelessly by taking in the previous state and returning the new state.
    """
    
    @staticmethod
    def evaluate(
        camera_id: str,
        zone_name: str,
        polygon: List[Tuple[float, float]],
        direction: str,  # "INBOUND", "OUTBOUND", "ANY"
        debounce_frames: int,
        track: Track,
        foot_point: Tuple[float, float],
        prev_state: Optional[FenceState] = None
    ) -> Tuple[Optional[Event], FenceState]:
        
        if cv2 is None:
            raise ImportError("OpenCV required for pointPolygonTest")
            
        if prev_state is None:
            prev_state = FenceState()
            
        poly_np = np.array(polygon, dtype=np.int32)
        
        # 1. Determine current raw state
        res = cv2.pointPolygonTest(poly_np, (float(foot_point[0]), float(foot_point[1])), False)
        current_is_inside = (res >= 0)
        
        # 2. Update consecutive frames for debouncing
        if current_is_inside == prev_state.is_inside:
            consecutive = prev_state.consecutive_frames + 1
        else:
            consecutive = 1
            
        new_state = FenceState(
            is_inside=current_is_inside,
            consecutive_frames=consecutive,
            confirmed_inside=prev_state.confirmed_inside
        )
        
        event = None
        
        # 3. Apply debounce logic
        if consecutive >= debounce_frames and current_is_inside != prev_state.confirmed_inside:
            # The raw state has been stable long enough to confirm a state change
            new_state.confirmed_inside = current_is_inside
            
            trigger = False
            intrusion_dir = ""
            direction = direction.upper()
            
            if current_is_inside:
                # Transition: Outside -> Inside
                if direction in ("INBOUND", "ANY"):
                    trigger = True
                    intrusion_dir = "INBOUND"
            else:
                # Transition: Inside -> Outside
                if direction in ("OUTBOUND", "ANY"):
                    trigger = True
                    intrusion_dir = "OUTBOUND"
                    
            if trigger:
                event = EventFactory.create(
                    event_type=EventType.VIRTUAL_FENCE_INTRUSION,
                    camera_id=camera_id,
                    severity=Severity.HIGH,
                    track_id=track.track_id,
                    confidence=track.confidence,
                    metadata={
                        "zone": zone_name,
                        "direction": intrusion_dir,
                        "class_name": track.class_name
                    }
                )
                
        return event, new_state
