import io
import logging
from datetime import datetime, timezone
from datetime import timedelta
from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

class MinIOService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_EVIDENCE_BUCKET

    def health_check(self) -> bool:
        """Check if MinIO is reachable and bucket exists."""
        try:
            return self.client.bucket_exists(self.bucket_name)
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False

    def _generate_object_path(self, camera_id: str, event_id: str, filename: str) -> str:
        """Generate the path: alerts/{camera_id}/{YYYY}/{MM}/{DD}/{event_id}/{filename}"""
        now = datetime.now(timezone.utc)
        return f"alerts/{camera_id}/{now.year}/{now.month:02d}/{now.day:02d}/{event_id}/{filename}"

    def upload_snapshot(self, camera_id: str, event_id: str, image_bytes: bytes) -> str:
        """Upload a snapshot and return the media_ref URI."""
        object_name = self._generate_object_path(camera_id, event_id, "snapshot.jpg")
        
        self.client.put_object(
            self.bucket_name,
            object_name,
            data=io.BytesIO(image_bytes),
            length=len(image_bytes),
            content_type="image/jpeg"
        )
        return f"s3://{self.bucket_name}/{object_name}"

    def upload_clip(self, camera_id: str, event_id: str, video_bytes: bytes) -> str:
        """Upload a video clip and return the media_ref URI."""
        object_name = self._generate_object_path(camera_id, event_id, "clip.mp4")
        
        self.client.put_object(
            self.bucket_name,
            object_name,
            data=io.BytesIO(video_bytes),
            length=len(video_bytes),
            content_type="video/mp4"
        )
        return f"s3://{self.bucket_name}/{object_name}"

    def get_presigned_url(self, media_ref: str, expires_in_seconds: int = 3600) -> str:
        """Translate a media_ref (s3://bucket/path) to a presigned URL."""
        if not media_ref.startswith(f"s3://{self.bucket_name}/"):
            raise ValueError(f"Invalid media_ref format: {media_ref}")
        
        object_name = media_ref.replace(f"s3://{self.bucket_name}/", "", 1)
        
        return self.client.presigned_get_object(
            self.bucket_name,
            object_name,
            expires=timedelta(seconds=expires_in_seconds)
        )

    def delete_evidence(self, media_ref: str) -> bool:
        """Parse media_ref and delete the object."""
        if not media_ref.startswith(f"s3://{self.bucket_name}/"):
            raise ValueError(f"Invalid media_ref format: {media_ref}")
            
        object_name = media_ref.replace(f"s3://{self.bucket_name}/", "", 1)
        
        try:
            self.client.remove_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            logger.error(f"Error deleting {media_ref}: {e}")
            return False
