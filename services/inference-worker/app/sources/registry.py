import logging
from typing import Dict, Type

from app.sources.camera_source import (
    CameraConfig,
    CameraSource,
    FileCameraSource,
    WebcamSource,
    RTSPCameraSource
)

logger = logging.getLogger(__name__)

class CameraRegistry:
    """Registry to instantiate the correct CameraSource based on config."""
    
    _sources: Dict[str, Type[CameraSource]] = {
        'file': FileCameraSource,
        'webcam': WebcamSource,
        'rtsp': RTSPCameraSource
    }

    @classmethod
    def register(cls, source_type: str, source_class: Type[CameraSource]):
        cls._sources[source_type.lower()] = source_class

    @classmethod
    def create(cls, config: CameraConfig) -> CameraSource:
        source_type = config.source_type.lower()
        if source_type not in cls._sources:
            raise ValueError(f"Unknown camera source_type: {source_type}")
        
        source_class = cls._sources[source_type]
        logger.info(f"Creating camera source of type '{source_type}' for {config.camera_id}")
        return source_class(config)
