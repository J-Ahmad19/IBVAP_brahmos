import pytest
from unittest.mock import MagicMock, patch

from app.sources.camera_source import (
    CameraConfig,
    FileCameraSource,
    WebcamSource,
    RTSPCameraSource
)
from app.sources.registry import CameraRegistry


@pytest.fixture
def mock_cv2():
    with patch('app.sources.camera_source.cv2') as mock:
        yield mock


def test_file_source_valid_and_eof_loop(mock_cv2):
    """Test reading from a valid file and looping on EOF."""
    # Setup mock VideoCapture
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    
    # First call to read() returns success and a fake frame
    # Second call returns failure (EOF)
    # Third call (after looping) returns success and a fake frame
    mock_cap.read.side_effect = [
        (True, "frame1"),
        (False, None),
        (True, "frame2")
    ]
    mock_cv2.VideoCapture.return_value = mock_cap
    
    config = CameraConfig(camera_id="cam-1", name="Test File", source_type="file", source_uri="test.mp4")
    source = FileCameraSource(config)
    
    assert source.health() is True
    
    # 1. Read first frame
    success, frame = source.read()
    assert success is True
    assert frame == "frame1"
    
    # 2. Read second frame (EOF encountered, should loop)
    success, frame = source.read()
    assert success is True
    assert frame == "frame2"
    
    # Assert that it reset to frame 0
    mock_cap.set.assert_called_once_with(mock_cv2.CAP_PROP_POS_FRAMES, 0)
    
    source.close()
    mock_cap.release.assert_called_once()


def test_invalid_file(mock_cv2):
    """Test handling of an invalid file or failed connection."""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False  # Failed to open
    mock_cv2.VideoCapture.return_value = mock_cap
    
    config = CameraConfig(camera_id="cam-2", name="Invalid File", source_type="file", source_uri="missing.mp4")
    source = FileCameraSource(config)
    
    assert source.health() is False
    
    success, frame = source.read()
    assert success is False
    assert frame is None


def test_webcam_unavailable(mock_cv2):
    """Test handling of an unavailable webcam."""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mock_cv2.VideoCapture.return_value = mock_cap
    
    config = CameraConfig(camera_id="cam-3", name="Webcam", source_type="webcam", source_uri="99")
    source = WebcamSource(config)
    
    assert source.health() is False
    success, frame = source.read()
    assert success is False
    
    # Verify it attempted to convert "99" to integer 99
    mock_cv2.VideoCapture.assert_called_with(99)


def test_rtsp_interface():
    """Test the RTSP stub."""
    config = CameraConfig(camera_id="cam-4", name="RTSP", source_type="rtsp", source_uri="rtsp://test")
    source = RTSPCameraSource(config)
    
    # RTSP is a stub in Phase 1, it should always be unhealthy and fail reads
    assert source.health() is False
    success, frame = source.read()
    assert success is False


def test_registry_creation():
    """Test the CameraRegistry correctly routes config to the right class."""
    config_file = CameraConfig(camera_id="c1", name="f", source_type="file", source_uri="1.mp4")
    source = CameraRegistry.create(config_file)
    assert isinstance(source, FileCameraSource)
    
    config_webcam = CameraConfig(camera_id="c2", name="w", source_type="webcam", source_uri="0")
    source = CameraRegistry.create(config_webcam)
    assert isinstance(source, WebcamSource)
    
    config_rtsp = CameraConfig(camera_id="c3", name="r", source_type="rtsp", source_uri="rtsp://")
    source = CameraRegistry.create(config_rtsp)
    assert isinstance(source, RTSPCameraSource)
    
    with pytest.raises(ValueError):
        invalid_config = CameraConfig(camera_id="c4", name="i", source_type="unknown", source_uri="")
        CameraRegistry.create(invalid_config)
