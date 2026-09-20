import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter

from app.core.config import settings

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self, host: str = settings.QDRANT_HOST, port: int = settings.QDRANT_PORT):
        self.client = QdrantClient(host=host, port=port)
        self.face_collection = "face_watchlist"
        self.plate_collection = "plate_watchlist"

    def health_check(self) -> bool:
        """Check if Qdrant is reachable and healthy."""
        try:
            # simple collections list to verify connectivity
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    def create_collections(self):
        """Ensure the necessary collections exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        
        if self.face_collection not in collections:
            self.client.create_collection(
                collection_name=self.face_collection,
                vectors_config=VectorParams(size=settings.FACE_VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Created collection: {self.face_collection}")

        if self.plate_collection not in collections:
            self.client.create_collection(
                collection_name=self.plate_collection,
                vectors_config=VectorParams(size=settings.PLATE_VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Created collection: {self.plate_collection}")

    def delete_collection(self, collection_name: str):
        """Drop a collection if it exists."""
        self.client.delete_collection(collection_name=collection_name)
        logger.info(f"Deleted collection: {collection_name}")

    # --- FACE METHODS ---

    def upsert_face(self, vector_id: str, vector: List[float], payload: Dict[str, Any] = None):
        """Insert or update a face vector."""
        if len(vector) != settings.FACE_VECTOR_SIZE:
            raise ValueError(f"Vector size {len(vector)} does not match face config {settings.FACE_VECTOR_SIZE}")
        
        self.client.upsert(
            collection_name=self.face_collection,
            points=[PointStruct(id=vector_id, vector=vector, payload=payload or {})]
        )

    def search_face(self, vector: List[float], limit: int = 5, query_filter: Optional[Filter] = None) -> List[Any]:
        """Search for similar face vectors."""
        if len(vector) != settings.FACE_VECTOR_SIZE:
            raise ValueError(f"Vector size {len(vector)} does not match face config {settings.FACE_VECTOR_SIZE}")

        return self.client.search(
            collection_name=self.face_collection,
            query_vector=vector,
            limit=limit,
            query_filter=query_filter
        )

    def delete_face(self, vector_id: str):
        """Delete a face vector by ID."""
        self.client.delete(
            collection_name=self.face_collection,
            points_selector=[vector_id]
        )

    # --- PLATE METHODS ---

    def upsert_plate(self, vector_id: str, vector: List[float], payload: Dict[str, Any] = None):
        """Insert or update a plate vector."""
        if len(vector) != settings.PLATE_VECTOR_SIZE:
            raise ValueError(f"Vector size {len(vector)} does not match plate config {settings.PLATE_VECTOR_SIZE}")
        
        self.client.upsert(
            collection_name=self.plate_collection,
            points=[PointStruct(id=vector_id, vector=vector, payload=payload or {})]
        )

    def search_plate(self, vector: List[float], limit: int = 5, query_filter: Optional[Filter] = None) -> List[Any]:
        """Search for similar plate vectors."""
        if len(vector) != settings.PLATE_VECTOR_SIZE:
            raise ValueError(f"Vector size {len(vector)} does not match plate config {settings.PLATE_VECTOR_SIZE}")

        return self.client.search(
            collection_name=self.plate_collection,
            query_vector=vector,
            limit=limit,
            query_filter=query_filter
        )

    def delete_plate(self, vector_id: str):
        """Delete a plate vector by ID."""
        self.client.delete(
            collection_name=self.plate_collection,
            points_selector=[vector_id]
        )
