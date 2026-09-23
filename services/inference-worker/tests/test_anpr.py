import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.models.anpr import ANPRModule, OCREngine, PaddleOCREngine

class MockTrack:
    def __init__(self, class_name, confidence, bbox, track_id):
        self.class_name = class_name
        self.confidence = confidence
        self.bbox = bbox
        self.track_id = track_id

class MockOCREngine(OCREngine):
    def recognize(self, image: np.ndarray):
        # Dummy OCR result for tests
        return [{
            "text": "ABC-123",
            "confidence": 0.95,
            "bbox": [10, 10, 50, 20]
        }]

def test_anpr_module_conditional_execution():
    # Setup mock OCR engine and ANPR module
    engine = MockOCREngine()
    anpr = ANPRModule(ocr_engine=engine, vehicle_threshold=0.5)
    
    # 100x100 fake frame
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Tracks
    tracks = [
        # Valid vehicle
        MockTrack("car", 0.8, [10, 10, 90, 90], "car_1"),
        # Valid vehicle but low confidence
        MockTrack("truck", 0.4, [0, 0, 50, 50], "truck_1"),
        # Not a vehicle
        MockTrack("person", 0.9, [20, 20, 30, 40], "person_1"),
        # Out of bounds bbox or invalid
        MockTrack("bus", 0.9, [110, 110, 120, 120], "bus_1")
    ]
    
    # Run ANPR
    results = anpr.process(frame, tracks)
    
    # Only "car_1" should have been processed
    assert len(results) == 1
    res = results[0]
    
    assert res.plate_text == "ABC-123"
    assert res.ocr_confidence == 0.95
    assert res.track_id == "car_1"
    
    # Global bbox calculation: car local starts at 10,10. local bbox is 10,10,50,20.
    # Global = 10+10, 10+10, 10+50, 10+20 => [20, 20, 60, 30]
    assert res.global_bbox == [20, 20, 60, 30]

@patch("app.models.anpr.PaddleOCR")
def test_paddleocr_engine_initialization(mock_paddleocr):
    # If PaddleOCR is available, it should initialize
    engine = PaddleOCREngine(lang='en')
    mock_paddleocr.assert_called_once_with(use_angle_cls=False, lang='en', show_log=False)

def test_paddleocr_engine_fallback_if_not_installed():
    # If PaddleOCR isn't installed, engine should still initialize safely but return []
    with patch("app.models.anpr.PaddleOCR", None):
        engine = PaddleOCREngine()
        assert engine.ocr is None
        
        # recognize should safely return empty list
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        assert engine.recognize(frame) == []
