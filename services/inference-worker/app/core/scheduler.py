import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
from dataclasses import dataclass

from app.sources.camera_source import CameraConfig

logger = logging.getLogger(__name__)

@dataclass
class SchedulerConfig:
    global_inference_fps: int = 15
    min_camera_fps: float = 1.0
    max_camera_fps: float = 5.0
    queue_size: int = 5


class CameraScheduler:
    """
    Shared CPU-Aware Scheduler.
    Provides a fair, priority-weighted round-robin distribution of a single global 
    inference budget to prevent camera monopolization.
    """
    def __init__(self, config: SchedulerConfig):
        self.config = config
        self.cameras: Dict[str, CameraConfig] = {}
        self.queues: Dict[str, deque] = {}
        
        self.last_sampled: Dict[str, float] = {}
        self.processed_timestamps: Dict[str, deque] = {}
        
        self._schedule: List[str] = []
        self._current_idx: int = 0
        self._global_processed: deque = deque(maxlen=50)

    def add_camera(self, camera: CameraConfig):
        self.cameras[camera.camera_id] = camera
        self.queues[camera.camera_id] = deque(maxlen=self.config.queue_size)
        self.last_sampled[camera.camera_id] = 0.0
        self.processed_timestamps[camera.camera_id] = deque(maxlen=20)
        self._rebuild_schedule()

    def remove_camera(self, camera_id: str):
        self.cameras.pop(camera_id, None)
        self.queues.pop(camera_id, None)
        self.last_sampled.pop(camera_id, None)
        self.processed_timestamps.pop(camera_id, None)
        self._rebuild_schedule()

    def _rebuild_schedule(self):
        """Builds a weighted round-robin array based on camera priority."""
        schedule = []
        for cam in self.cameras.values():
            if not cam.enabled:
                continue
            # Higher priority number = more slots in the round-robin cycle
            weight = max(1, cam.priority)
            schedule.extend([cam.camera_id] * weight)
        
        # Sort or interleave for better distribution, but simple append works for small sets
        self._schedule = schedule
        self._current_idx = 0

    def should_sample(self, camera_id: str) -> bool:
        """
        Determines if a camera should capture a frame right now based on MAX_CAMERA_FPS limit.
        """
        now = time.time()
        last = self.last_sampled.get(camera_id, 0.0)
        
        # Throttle to max_camera_fps
        if (now - last) < (1.0 / self.config.max_camera_fps):
            return False
            
        return True

    def enqueue(self, camera_id: str, frame: Any):
        """
        Enqueues a frame. If the bounded queue is full, drops the oldest frame.
        """
        if camera_id not in self.queues:
            return
            
        q = self.queues[camera_id]
        if len(q) >= self.config.queue_size:
            # Dropped-frame policy: shed oldest to keep latency low
            q.popleft()
            
        q.append(frame)
        self.last_sampled[camera_id] = time.time()

    def next_camera(self) -> Optional[Tuple[str, Any]]:
        """
        Returns (camera_id, frame) of the next camera to process based on round-robin.
        """
        if not self._schedule:
            return None
            
        start_idx = self._current_idx
        
        while True:
            cam_id = self._schedule[self._current_idx]
            self._current_idx = (self._current_idx + 1) % len(self._schedule)
            
            q = self.queues.get(cam_id)
            if q and len(q) > 0:
                frame = q.popleft()
                now = time.time()
                self.processed_timestamps[cam_id].append(now)
                self._global_processed.append(now)
                return cam_id, frame
                
            # If we've checked every slot in the schedule and found nothing
            if self._current_idx == start_idx:
                return None

    def metrics(self) -> Dict[str, Any]:
        """Calculates effective FPS for the global worker and per-camera."""
        metrics = {
            "global_fps": self._calc_fps(self._global_processed),
            "cameras": {}
        }
        
        for cam_id, cam in self.cameras.items():
            qsize = len(self.queues.get(cam_id, []))
            fps = self._calc_fps(self.processed_timestamps.get(cam_id, deque()))
            metrics["cameras"][cam_id] = {
                "priority": cam.priority,
                "queue_size": qsize,
                "effective_fps": round(fps, 2)
            }
            
        return metrics

    def _calc_fps(self, timestamps: deque) -> float:
        if len(timestamps) < 2:
            return 0.0
        duration = timestamps[-1] - timestamps[0]
        if duration <= 0:
            return 0.0
        return (len(timestamps) - 1) / duration
