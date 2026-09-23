import io
import cv2
import logging
import asyncio
from datetime import datetime, timezone
import numpy as np
from minio import Minio
import os

from app.events.schema import Event

logger = logging.getLogger(__name__)

class EvidenceService:
    """
    Handles capturing and uploading evidence to MinIO without blocking the inference loop indefinitely.
    """
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")
        self.secret_key = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.bucket_name = os.getenv("MINIO_BUCKET_ALERTS", "alerts")
        
        # Initialize Minio client (synchronous, but we will run operations in threadpool)
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

    def _generate_object_path(self, camera_id: str, event_id: str, filename: str) -> str:
        now = datetime.now(timezone.utc)
        return f"alerts/{camera_id}/{now.year}/{now.month:02d}/{now.day:02d}/{event_id}/{filename}"

    def _sync_upload(self, camera_id: str, event_id: str, image_bytes: bytes) -> str:
        object_name = self._generate_object_path(camera_id, event_id, "snapshot.jpg")
        
        self.client.put_object(
            self.bucket_name,
            object_name,
            data=io.BytesIO(image_bytes),
            length=len(image_bytes),
            content_type="image/jpeg"
        )
        return f"s3://{self.bucket_name}/{object_name}"

    async def attach_evidence(self, event: Event, frame: np.ndarray) -> Event:
        """
        Takes an Event and a frame, creates a JPEG snapshot, uploads it to MinIO asynchronously,
        updates the event's media_ref, and returns the updated event.
        If MinIO fails, logs the error, leaves media_ref None, and returns the event anyway.
        """
        try:
            # Encode frame to JPEG
            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                logger.error(f"Failed to encode frame to JPEG for event {event.event_id}")
                return event
                
            image_bytes = buffer.tobytes()
            
            # Offload synchronous Minio upload to a thread to avoid blocking asyncio event loop
            media_ref = await asyncio.to_thread(self._sync_upload, event.camera_id, event.event_id, image_bytes)
            event.media_ref = media_ref
            logger.debug(f"Attached evidence {media_ref} to event {event.event_id}")
            
        except Exception as e:
            logger.error(f"MinIO temporarily failed or evidence upload failed for event {event.event_id}: {e}")
            
        return event
