import time
import logging
from typing import List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import os

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logger = logging.getLogger(__name__)

@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # [x_min, y_min, x_max, y_max]
    timestamp: datetime


class DetectorInterface:
    def load(self):
        pass
    def warmup(self):
        pass
    def detect(self, frame: Any) -> List[Detection]:
        pass
    def close(self):
        pass


class YOLODetector(DetectorInterface):
    """
    YOLOv8n Adapter for IBVAP.
    Choice of YOLOv8n: YOLOv8n is extremely stable, lightweight, and has 
    flawless native export support for OpenVINO and ONNX Runtime. It serves
    perfectly as the base detector for the CPU prototype.
    """
    def __init__(self, model_path: str, conf_threshold: float = 0.25):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.model = None
        self._is_loaded = False

    def load(self):
        if YOLO is None:
            logger.error("Ultralytics package is not installed.")
            raise ImportError("ultralytics is required for YOLODetector")
            
        if not os.path.exists(self.model_path):
            logger.error(f"Model file not found at {self.model_path}")
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        logger.info(f"Loading YOLOv8n model from {self.model_path}...")
        # ultralytics automatically picks up the OpenVINO or ONNX runtime 
        # based on the extension (.onnx or _openvino_model/)
        self.model = YOLO(self.model_path, task='detect')
        self._is_loaded = True
        logger.info("Model loaded successfully.")

    def warmup(self):
        if not self._is_loaded:
            self.load()
            
        logger.info("Warming up model with synthetic frame...")
        import numpy as np
        # Create a synthetic 640x640 frame for warmup
        dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        self.detect(dummy_frame)
        logger.info("Warmup complete.")

    def detect(self, frame: Any) -> List[Detection]:
        if not self._is_loaded:
            raise RuntimeError("Detector is not loaded. Call load() first.")
            
        if frame is None or getattr(frame, 'size', 0) == 0:
            logger.warning("Empty frame passed to detector.")
            return []

        start_time = time.time()
        
        # We enforce verbose=False so the stdout doesn't get flooded in production.
        results = self.model.predict(
            source=frame, 
            conf=self.conf_threshold, 
            verbose=False,
            device='cpu' # Enforce CPU for Phase 1
        )
        
        end_time = time.time()
        latency = (end_time - start_time) * 1000.0
        
        detections = []
        now = datetime.now(timezone.utc)
        
        # Translate Ultralytics abstractions to IBVAP primitive schema
        for result in results:
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue
                
            for box in boxes:
                conf = float(box.conf[0].cpu().item())
                if conf < self.conf_threshold:
                    continue
                    
                cls_id = int(box.cls[0].cpu().item())
                class_name = result.names.get(cls_id, "unknown")
                
                # xyxy format
                coords = box.xyxy[0].cpu().tolist()
                bbox = (coords[0], coords[1], coords[2], coords[3])
                
                detections.append(Detection(
                    class_name=class_name,
                    confidence=conf,
                    bbox=bbox,
                    timestamp=now
                ))
                
        logger.debug(f"YOLODetector processed frame in {latency:.2f}ms. Found {len(detections)} objects.")
        return detections

    def close(self):
        self.model = None
        self._is_loaded = False
        logger.info("Detector closed.")
