import numpy as np
import pytest
from app.models.night import NightPipeline

try:
    import cv2
except ImportError:
    cv2 = None

@pytest.mark.skipif(cv2 is None, reason="OpenCV required")
def test_night_pipeline_enhancement():
    pipeline = NightPipeline()
    
    # Create a synthetic darkened frame
    frame = np.ones((100, 100, 3), dtype=np.uint8) * 10
    
    enhanced = pipeline.enhance_frame(frame)
    
    # The enhanced frame should have higher luminance than the original darkened frame
    # due to CLAHE spreading the histogram.
    orig_lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    enh_lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
    
    orig_l, _, _ = cv2.split(orig_lab)
    enh_l, _, _ = cv2.split(enh_lab)
    
    assert np.mean(enh_l) > np.mean(orig_l)

@pytest.mark.skipif(cv2 is None, reason="OpenCV required")
def test_night_pipeline_process_no_fallback():
    pipeline = NightPipeline(motion_area_threshold=500, confidence_threshold=0.5)
    
    # Same frames, no motion
    frame1 = np.ones((100, 100, 3), dtype=np.uint8) * 50
    frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 50
    
    # High confidence detector -> no fallback
    def mock_detector_high(enh_frame):
        return 0.8
        
    res = pipeline.process(frame2, frame1, mock_detector_high)
    assert res.motion_score == 0.0
    assert res.fallback_triggered is False
    assert res.enhanced_frame is not None

@pytest.mark.skipif(cv2 is None, reason="OpenCV required")
def test_night_pipeline_process_with_fallback():
    pipeline = NightPipeline(motion_area_threshold=100, confidence_threshold=0.5)
    
    # Create synthetic darkened frames with motion
    frame1 = np.ones((100, 100, 3), dtype=np.uint8) * 10
    frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 10
    
    # Add a "moving" object (change a 20x20 area, 400 pixels)
    frame2[40:60, 40:60] = 100
    
    # Low confidence detector
    def mock_detector_low(enh_frame):
        return 0.2
        
    res = pipeline.process(frame2, frame1, mock_detector_low)
    
    # Motion score should be 400
    assert res.motion_score == 400.0
    # Confidence is low (0.2 < 0.5) AND motion is high (400 > 100) -> fallback triggers
    assert res.fallback_triggered is True

@pytest.mark.skipif(cv2 is None, reason="OpenCV required")
def test_night_pipeline_first_frame():
    pipeline = NightPipeline()
    frame1 = np.ones((100, 100, 3), dtype=np.uint8) * 10
    
    def mock_detector(enh_frame):
        return 0.2
        
    res = pipeline.process(frame1, None, mock_detector)
    assert res.motion_score == 0.0
    assert res.fallback_triggered is False
