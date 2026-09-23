import numpy as np
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from insightface.app import FaceAnalysis
except ImportError:
    FaceAnalysis = None

try:
    from qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None


@dataclass
class FaceMatch:
    matched: bool
    subject_id: Optional[str]
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]]


class FaceModule:
    """
    Phase 9A — INSIGHTFACE FACE MODULE
    Executes conditionally on person tracks (person crops) to avoid scanning full frames.
    """
    
    def __init__(self, qdrant_client=None, collection_name: str = "watchlist", match_threshold: float = 0.6):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.match_threshold = match_threshold
        
        self.app = None
        if FaceAnalysis is not None:
            # buffalo_s is a lightweight model bundle (det + rec)
            # We strictly enforce CPU execution per requirements
            self.app = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=0, det_size=(640, 640))
        else:
            logger.warning("InsightFace is not installed. Face module will return None.")

    def detect_face(self, person_crop: np.ndarray) -> Any:
        """
        Detects faces in a person crop and implicitly performs alignment.
        Returns the largest face object found, or None.
        """
        if self.app is None:
            return None
            
        faces = self.app.get(person_crop)
        if not faces:
            return None
            
        # Return the largest face by bounding box area to ensure we process the main subject
        largest_face = max(
            faces, 
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
        )
        return largest_face

    def generate_embedding(self, face_obj: Any) -> Optional[np.ndarray]:
        """
        Extracts the facial embedding from the aligned face object.
        InsightFace buffalo_s generates a 512-d feature vector.
        """
        if face_obj is None or getattr(face_obj, 'normed_embedding', None) is None:
            return None
        return face_obj.normed_embedding

    def normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        """
        Normalizes the embedding for cosine similarity search in Qdrant.
        """
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm

    def search_watchlist(self, embedding: np.ndarray) -> Tuple[bool, Optional[str], float]:
        """
        Queries Qdrant for the closest match to the normalized embedding.
        """
        if self.qdrant_client is None:
            return False, None, 0.0
            
        try:
            hits = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=embedding.tolist(),
                limit=1,
                with_payload=True
            )
            
            if hits:
                best_hit = hits[0]
                if best_hit.score >= self.match_threshold:
                    subject_id = best_hit.payload.get("subject_id", str(best_hit.id))
                    return True, subject_id, float(best_hit.score)
        except Exception as e:
            logger.error(f"Error searching Qdrant watchlist: {e}")
            
        return False, None, 0.0

    def process(self, person_crop: np.ndarray, face_analysis_enabled: bool = True) -> Optional[FaceMatch]:
        """
        Executes the full pipeline:
        person crop -> face detect -> align -> embedding -> normalize -> Qdrant search.
        
        IMPORTANT: This must only be called conditionally (e.g. if the track is a 'person' 
        and face_analysis_enabled is True) to avoid unnecessary computation.
        """
        if not face_analysis_enabled:
            return None
            
        # 1. & 2. Face Detect and Align (InsightFace handles alignment internally)
        face = self.detect_face(person_crop)
        if face is None:
            return None
            
        # 3. Embedding extraction
        embedding = self.generate_embedding(face)
        if embedding is None:
            return None
            
        # 4. Normalize embedding
        normalized_emb = self.normalize_embedding(embedding)
        
        # 5. Qdrant Search
        is_match, subject_id, confidence = self.search_watchlist(normalized_emb)
        
        bbox = None
        if face.bbox is not None:
            bbox = (int(face.bbox[0]), int(face.bbox[1]), int(face.bbox[2]), int(face.bbox[3]))
            
        return FaceMatch(
            matched=is_match,
            subject_id=subject_id,
            confidence=confidence,
            bbox=bbox
        )
