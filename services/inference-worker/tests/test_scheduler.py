import pytest
import time
from unittest.mock import patch

from app.core.scheduler import CameraScheduler, SchedulerConfig
from app.sources.camera_source import CameraConfig


@pytest.fixture
def scheduler():
    config = SchedulerConfig(
        global_inference_fps=10,
        min_camera_fps=1.0,
        max_camera_fps=5.0,
        queue_size=3
    )
    return CameraScheduler(config)


def test_enqueue_and_drop_policy(scheduler):
    """Verify that bounded queue drops oldest frames."""
    cam = CameraConfig(camera_id="cam-1", name="Test", source_type="file", source_uri="path")
    scheduler.add_camera(cam)
    
    # Enqueue 5 frames (queue_size is 3)
    for i in range(5):
        scheduler.enqueue("cam-1", f"frame-{i}")
        
    q = scheduler.queues["cam-1"]
    assert len(q) == 3
    # The oldest frames (0, 1) should be dropped
    assert q[0] == "frame-2"
    assert q[-1] == "frame-4"


def test_should_sample(scheduler):
    """Verify max FPS throttling."""
    cam = CameraConfig(camera_id="cam-1", name="Test", source_type="file", source_uri="path")
    scheduler.add_camera(cam)
    
    with patch('app.core.scheduler.time.time') as mock_time:
        mock_time.return_value = 100.0
        # First sample should be allowed
        assert scheduler.should_sample("cam-1") is True
        scheduler.enqueue("cam-1", "frame-1")
        
        # Advance time by 0.1s (10 FPS rate, limit is 5.0 FPS = 0.2s)
        mock_time.return_value = 100.1
        assert scheduler.should_sample("cam-1") is False
        
        # Advance time by 0.25s (allowed)
        mock_time.return_value = 100.25
        assert scheduler.should_sample("cam-1") is True


def test_fairness_and_priority(scheduler):
    """Verify weighted round-robin distribution."""
    cam1 = CameraConfig(camera_id="cam-1", name="C1", priority=1, source_type="file", source_uri="")
    cam2 = CameraConfig(camera_id="cam-2", name="C2", priority=2, source_type="file", source_uri="")
    cam3 = CameraConfig(camera_id="cam-3", name="C3", priority=1, source_type="file", source_uri="")
    
    scheduler.add_camera(cam1)
    scheduler.add_camera(cam2)
    scheduler.add_camera(cam3)
    
    # Fill all queues
    for i in range(3):
        scheduler.enqueue("cam-1", f"f1-{i}")
        scheduler.enqueue("cam-2", f"f2-{i}")
        scheduler.enqueue("cam-3", f"f3-{i}")
        
    # Expected schedule: cam-1 (x1), cam-2 (x2), cam-3 (x1)
    # Order might be exactly [cam-1, cam-2, cam-2, cam-3] based on current append logic
    
    processed = []
    for _ in range(4):
        res = scheduler.next_camera()
        if res:
            processed.append(res[0])
            
    assert processed.count("cam-1") == 1
    assert processed.count("cam-2") == 2
    assert processed.count("cam-3") == 1


def test_metrics_empty(scheduler):
    """Verify metrics don't crash when empty."""
    cam = CameraConfig(camera_id="cam-1", name="Test", priority=1, source_type="file", source_uri="")
    scheduler.add_camera(cam)
    
    metrics = scheduler.metrics()
    assert metrics["global_fps"] == 0.0
    assert metrics["cameras"]["cam-1"]["queue_size"] == 0
    assert metrics["cameras"]["cam-1"]["effective_fps"] == 0.0


def test_metrics_calculation(scheduler):
    """Verify basic FPS calculation math."""
    cam = CameraConfig(camera_id="cam-1", name="Test", priority=1, source_type="file", source_uri="")
    scheduler.add_camera(cam)
    
    scheduler.enqueue("cam-1", "f1")
    scheduler.enqueue("cam-1", "f2")
    
    with patch('app.core.scheduler.time.time') as mock_time:
        mock_time.return_value = 100.0
        scheduler.next_camera()
        
        mock_time.return_value = 101.0  # 1 second later
        scheduler.next_camera()
        
        metrics = scheduler.metrics()
        # 2 frames processed over 1 second = 1.0 FPS
        assert metrics["global_fps"] == 1.0
        assert metrics["cameras"]["cam-1"]["effective_fps"] == 1.0
