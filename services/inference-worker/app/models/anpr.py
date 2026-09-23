from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

class PlateMatch:
    def __init__(
        self,
        plate_text: str,
        ocr_confidence: float,
        global_bbox: List[int],
        track_id: Optional[str] = None
    ):
        self.plate_text = plate_text
        self.ocr_confidence = ocr_confidence
        self.global_bbox = global_bbox
        self.track_id = track_id

class OCREngine(ABC):
    """
    Abstract interface for OCR engines.
    """
    @abstractmethod
    def recognize(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Accepts a cropped image array (BGR or RGB as required by the engine).
        Returns a list of dictionaries, each containing:
        {
            "text": str,
            "confidence": float,
            "bbox": [x1, y1, x2, y2] # relative to the crop
        }
        """
        pass

class PaddleOCREngine(OCREngine):
    """
    Implementation of OCREngine using PaddleOCR.
    """
    def __init__(self, lang='en', use_angle_cls=False):
        if PaddleOCR is None:
            logger.warning("PaddleOCR is not installed. Mocking OCR results.")
            self.ocr = None
        else:
            # Initialize lightweight mobile model
            self.ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang, show_log=False)

    def recognize(self, image: np.ndarray) -> List[Dict[str, Any]]:
        if self.ocr is None:
            return []

        # PaddleOCR returns a list of results. 
        # Format: [[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ('text', confidence)], ...]
        # Note: image should be RGB or BGR depending on PaddleOCR expectations, 
        # PaddleOCR handles BGR from cv2.imread natively.
        try:
            results = self.ocr.ocr(image, cls=False)
        except Exception as e:
            logger.error(f"PaddleOCR inference failed: {e}")
            return []

        if not results or not results[0]:
            return []
            
        plates = []
        for line in results[0]:
            bbox, (text, confidence) = line
            # bbox is a list of 4 points: [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
            # Convert to [x1, y1, x2, y2]
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            x1, y1, x2, y2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
            
            plates.append({
                "text": text,
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2]
            })
            
        return plates


class ANPRModule:
    """
    Handles automatic number plate recognition on detected vehicles.
    """
    def __init__(self, ocr_engine: OCREngine, vehicle_threshold: float = 0.5):
        self.ocr_engine = ocr_engine
        self.vehicle_threshold = vehicle_threshold
        # Common vehicle classes (e.g., from COCO dataset used by YOLO)
        self.vehicle_classes = {"car", "truck", "bus", "motorcycle"}

    def process(self, frame: np.ndarray, tracks: List[Any]) -> List[PlateMatch]:
        """
        Processes a full frame given vehicle tracks/detections.
        """
        plate_matches = []
        height, width = frame.shape[:2]

        for track in tracks:
            # Condition 1: Must be a vehicle
            # Condition 2: Confidence must be >= VEHICLE_THRESHOLD
            # Assume track has attributes: class_name, confidence, bbox, track_id
            if track.class_name not in self.vehicle_classes:
                continue
                
            if track.confidence < self.vehicle_threshold:
                continue
                
            x1, y1, x2, y2 = track.bbox
            # Ensure bbox is within frame boundaries
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(width, int(x2))
            y2 = min(height, int(y2))
            
            if x2 <= x1 or y2 <= y1:
                continue
                
            vehicle_crop = frame[y1:y2, x1:x2]
            
            # Pass crop to OCR
            ocr_results = self.ocr_engine.recognize(vehicle_crop)
            
            for res in ocr_results:
                local_x1, local_y1, local_x2, local_y2 = res["bbox"]
                
                # Map back to global frame coordinates
                global_bbox = [
                    x1 + local_x1,
                    y1 + local_y1,
                    x1 + local_x2,
                    y1 + local_y2
                ]
                
                plate_matches.append(PlateMatch(
                    plate_text=res["text"],
                    ocr_confidence=res["confidence"],
                    global_bbox=global_bbox,
                    track_id=getattr(track, "track_id", None)
                ))

        return plate_matches
