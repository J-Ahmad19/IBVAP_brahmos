import numpy as np
from typing import Tuple, Optional, Callable, Any
from dataclasses import dataclass

try:
    import cv2
except ImportError:
    cv2 = None

@dataclass
class NightPipelineResult:
    enhanced_frame: np.ndarray
    motion_score: float
    fallback_triggered: bool


class NightPipeline:
    """
    Phase 8A — Night / Low-light Pipeline.
    Enhances low-light frames using CLAHE in LAB color space, 
    then evaluates motion against a fallback threshold if detector confidence remains low.
    """
    
    def __init__(
        self,
        clip_limit: float = 2.0,
        tile_grid_size: Tuple[int, int] = (8, 8),
        motion_pixel_threshold: int = 25,
        motion_area_threshold: int = 500,
        confidence_threshold: float = 0.5
    ):
        if cv2 is None:
            raise ImportError("OpenCV required for NightPipeline")
            
        self.clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        self.motion_pixel_threshold = motion_pixel_threshold
        self.motion_area_threshold = motion_area_threshold
        self.confidence_threshold = confidence_threshold

    def enhance_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Converts to LAB, applies CLAHE on luminance (L), and converts back to RGB (BGR).
        """
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_enhanced = self.clahe.apply(l)
        lab_enhanced = cv2.merge((l_enhanced, a, b))
        return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

    def calculate_motion(self, current_frame: np.ndarray, prev_frame: Optional[np.ndarray]) -> float:
        """
        Calculates motion score using cv2.absdiff on grayscale frames.
        Returns the number of pixels exceeding the motion_pixel_threshold.
        """
        if prev_frame is None:
            return 0.0
            
        gray_curr = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        
        diff = cv2.absdiff(gray_curr, gray_prev)
        _, thresh = cv2.threshold(diff, self.motion_pixel_threshold, 255, cv2.THRESH_BINARY)
        
        return float(cv2.countNonZero(thresh))

    def process(
        self, 
        current_frame: np.ndarray, 
        prev_frame: Optional[np.ndarray], 
        detector_callable: Callable[[np.ndarray], float]
    ) -> NightPipelineResult:
        """
        Executes the night pipeline:
        1. Enhances frame.
        2. Gets max confidence from the detector callable running on the enhanced frame.
        3. Calculates motion score between current and previous unenhanced frames.
        4. Triggers fallback (UNCLASSIFIED_MOVEMENT equivalent state) if confidence is low AND motion is high.
        
        Args:
            current_frame: The raw BGR frame.
            prev_frame: The previous raw BGR frame (for motion diff).
            detector_callable: A function that takes the enhanced frame and returns the max detection confidence.
        """
        enhanced_frame = self.enhance_frame(current_frame)
        
        max_confidence = detector_callable(enhanced_frame)
        
        motion_score = self.calculate_motion(current_frame, prev_frame)
        
        fallback_triggered = False
        if max_confidence < self.confidence_threshold and motion_score > self.motion_area_threshold:
            fallback_triggered = True
            
        return NightPipelineResult(
            enhanced_frame=enhanced_frame,
            motion_score=motion_score,
            fallback_triggered=fallback_triggered
        )
