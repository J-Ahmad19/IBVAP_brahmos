import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from insightface.app import FaceAnalysis
except ImportError:
    FaceAnalysis = None


class FaceEnrollmentService:
    """
    Handles face embedding extraction for the API (Watchlist Enrollment).
    """
    def __init__(self):
        self.app = None
        if FaceAnalysis is not None:
            self.app = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=0, det_size=(640, 640))
        else:
            logger.warning("InsightFace is not installed. Face enrollment will return mock/None embeddings.")

    def process_image(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Takes raw image bytes, decodes, detects the largest face, and returns its normalized embedding.
        """
        if self.app is None or cv2 is None:
            # Fallback for testing when dependencies aren't available
            return None
            
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")
            
        faces = self.app.get(img)
        if not faces:
            return None
            
        largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        
        embedding = getattr(largest_face, 'normed_embedding', None)
        if embedding is None:
            return None
            
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm

