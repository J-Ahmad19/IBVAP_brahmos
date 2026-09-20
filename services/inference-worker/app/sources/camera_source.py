import time
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    import cv2
except ImportError:
    cv2 = None

logger = logging.getLogger(__name__)

@dataclass
class CameraConfig:
    camera_id: str
    name: str
    source_type: str  # 'file', 'webcam', 'rtsp'
    source_uri: str
    location: Optional[str] = None
    zone: Optional[str] = None
    priority: int = 1
    enabled: bool = True

class CameraSource(ABC):
    def __init__(self, config: CameraConfig):
        self.config = config
        self.last_frame_ts: Optional[datetime] = None
        self._connected = False

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[Any]]:
        """Reads the next frame. Returns (success, frame)."""
        pass

    @abstractmethod
    def health(self) -> bool:
        """Returns True if the camera is healthy and connected."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes the camera connection."""
        pass

class FileCameraSource(CameraSource):
    def __init__(self, config: CameraConfig):
        super().__init__(config)
        self.cap = None
        self._connect()

    def _connect(self):
        if cv2 is None:
            logger.error("OpenCV not installed. Cannot open file.")
            self._connected = False
            return

        self.cap = cv2.VideoCapture(self.config.source_uri)
        if self.cap and self.cap.isOpened():
            self._connected = True
        else:
            self._connected = False
            logger.error(f"Failed to open video file: {self.config.source_uri}")

    def read(self) -> Tuple[bool, Optional[Any]]:
        if not self._connected or self.cap is None:
            self._connect()
            if not self._connected:
                return False, None

        success, frame = self.cap.read()
        
        if not success:
            # Handle EOF loop
            logger.info(f"File {self.config.source_uri} reached EOF. Looping.")
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            success, frame = self.cap.read()
            if not success:
                logger.error(f"Decode failure on loop for file: {self.config.source_uri}")
                return False, None

        self.last_frame_ts = datetime.now(timezone.utc)
        return True, frame

    def health(self) -> bool:
        return self._connected and self.cap is not None and self.cap.isOpened()

    def close(self) -> None:
        if self.cap:
            self.cap.release()
        self._connected = False


class WebcamSource(CameraSource):
    def __init__(self, config: CameraConfig):
        super().__init__(config)
        self.cap = None
        self._connect()

    def _connect(self):
        if cv2 is None:
            logger.error("OpenCV not installed.")
            self._connected = False
            return

        try:
            # Source URI should be an integer index
            camera_index = int(self.config.source_uri)
        except ValueError:
            logger.error(f"Webcam source_uri must be an integer, got: {self.config.source_uri}")
            self._connected = False
            return

        self.cap = cv2.VideoCapture(camera_index)
        if self.cap and self.cap.isOpened():
            self._connected = True
        else:
            self._connected = False
            logger.error(f"Failed to open webcam index: {camera_index}")

    def read(self) -> Tuple[bool, Optional[Any]]:
        if not self._connected or self.cap is None:
            return False, None

        success, frame = self.cap.read()
        if success:
            self.last_frame_ts = datetime.now(timezone.utc)
        return success, frame

    def health(self) -> bool:
        return self._connected and self.cap is not None and self.cap.isOpened()

    def close(self) -> None:
        if self.cap:
            self.cap.release()
        self._connected = False


class RTSPCameraSource(CameraSource):
    """
    RTSP Camera Source Stub.
    Not required for Phase 1 CPU prototype, disabled by default.
    """
    def __init__(self, config: CameraConfig):
        super().__init__(config)
        logger.info("RTSPCameraSource initialized as a stub for Phase 1.")
        self._connected = False

    def read(self) -> Tuple[bool, Optional[Any]]:
        # Stub implementation
        return False, None

    def health(self) -> bool:
        # Stub implementation
        return False

    def close(self) -> None:
        # Stub implementation
        pass
