import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from app.models.detector import YOLODetector, Detection


@pytest.fixture
def mock_yolo():
    with patch('app.models.detector.YOLO') as MockYOLO:
        yield MockYOLO


def test_model_not_found():
    detector = YOLODetector(model_path="non_existent.onnx")
    with patch('os.path.exists', return_value=False):
        with pytest.raises(FileNotFoundError):
            detector.load()


def test_detect_before_load():
    detector = YOLODetector(model_path="dummy.onnx")
    frame = np.zeros((100, 100, 3))
    with pytest.raises(RuntimeError, match="not loaded"):
        detector.detect(frame)


def test_empty_frame_handling(mock_yolo):
    detector = YOLODetector(model_path="dummy.onnx")
    detector._is_loaded = True  # Mock load
    
    # None frame
    assert detector.detect(None) == []
    
    # Empty array
    assert detector.detect(np.array([])) == []


def test_successful_detection(mock_yolo):
    detector = YOLODetector(model_path="dummy.onnx", conf_threshold=0.5)
    
    # Setup mock model and result
    mock_model_instance = MagicMock()
    mock_yolo.return_value = mock_model_instance
    detector.model = mock_model_instance
    detector._is_loaded = True
    
    # Create a mock result object matching Ultralytics structure
    mock_box = MagicMock()
    # Mock confidence > threshold
    mock_conf = MagicMock()
    mock_conf.cpu.return_value.item.return_value = 0.8
    mock_box.conf = [mock_conf]
    
    # Mock class ID
    mock_cls = MagicMock()
    mock_cls.cpu.return_value.item.return_value = 0
    mock_box.cls = [mock_cls]
    
    # Mock coords
    mock_coords = MagicMock()
    mock_coords.cpu.return_value.tolist.return_value = [10.0, 20.0, 30.0, 40.0]
    mock_box.xyxy = [mock_coords]
    
    mock_result = MagicMock()
    mock_result.boxes = [mock_box]
    mock_result.names = {0: "person"}
    
    mock_model_instance.predict.return_value = [mock_result]
    
    frame = np.zeros((640, 640, 3))
    detections = detector.detect(frame)
    
    assert len(detections) == 1
    det = detections[0]
    assert isinstance(det, Detection)
    assert det.class_name == "person"
    assert det.confidence == 0.8
    assert det.bbox == (10.0, 20.0, 30.0, 40.0)
    assert det.timestamp is not None
    
    # Verify strict CPU enforcement
    mock_model_instance.predict.assert_called_once()
    kwargs = mock_model_instance.predict.call_args[1]
    assert kwargs['device'] == 'cpu'
    assert kwargs['conf'] == 0.5


def test_confidence_threshold_filtering(mock_yolo):
    detector = YOLODetector(model_path="dummy.onnx", conf_threshold=0.9)
    detector._is_loaded = True
    
    mock_model_instance = MagicMock()
    detector.model = mock_model_instance
    
    # Create box with 0.8 confidence (should be filtered out because threshold is 0.9)
    mock_box = MagicMock()
    mock_conf = MagicMock()
    mock_conf.cpu.return_value.item.return_value = 0.8
    mock_box.conf = [mock_conf]
    mock_cls = MagicMock()
    mock_cls.cpu.return_value.item.return_value = 0
    mock_box.cls = [mock_cls]
    mock_coords = MagicMock()
    mock_coords.cpu.return_value.tolist.return_value = [0, 0, 10, 10]
    mock_box.xyxy = [mock_coords]
    
    mock_result = MagicMock()
    mock_result.boxes = [mock_box]
    mock_model_instance.predict.return_value = [mock_result]
    
    frame = np.zeros((10, 10, 3))
    detections = detector.detect(frame)
    
    # Assert it was filtered out by our explicit wrapper logic
    assert len(detections) == 0


def test_warmup(mock_yolo):
    detector = YOLODetector(model_path="dummy.onnx")
    
    with patch('os.path.exists', return_value=True):
        detector.warmup()
        
    assert detector._is_loaded is True
    # Verify predict was called with dummy frame
    assert detector.model.predict.call_count == 1
