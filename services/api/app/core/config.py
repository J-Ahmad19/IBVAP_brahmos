import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL", 
        "postgresql+asyncpg://ibvap:ibvap_secret@localhost:5432/ibvap_db"
    )

    # Qdrant
    QDRANT_HOST: str = os.environ.get("QDRANT_HOST", "qdrant")
    QDRANT_PORT: int = int(os.environ.get("QDRANT_PORT", 6333))
    
    # Vector Dimensions (ArcFace buffalo_s typically uses 512 for face)
    FACE_VECTOR_SIZE: int = int(os.environ.get("FACE_VECTOR_SIZE", 512))
    # Plates can use different feature extractor dimensions, defaulting to 512 for parity if generic vectors are used
    PLATE_VECTOR_SIZE: int = int(os.environ.get("PLATE_VECTOR_SIZE", 512))

    # MinIO / Object Storage
    MINIO_ENDPOINT: str = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY: str = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE: bool = os.environ.get("MINIO_SECURE", "false").lower() == "true"
    MINIO_EVIDENCE_BUCKET: str = os.environ.get("MINIO_EVIDENCE_BUCKET", "ibvap-evidence")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
