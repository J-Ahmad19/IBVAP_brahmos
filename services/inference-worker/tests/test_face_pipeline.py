import numpy as np
import pytest
from unittest.mock import MagicMock
from app.models.face import FaceModule, FaceMatch

def test_pipeline_known_watchlist_face():
    module = FaceModule()
    
    mock_app = MagicMock()
    module.app = mock_app
    mock_face = MagicMock()
    mock_face.bbox = [0, 0, 100, 100]
    mock_face.normed_embedding = np.random.rand(512).astype(np.float32)
    mock_app.get.return_value = [mock_face]
    
    mock_qdrant = MagicMock()
    module.qdrant_client = mock_qdrant
    mock_hit = MagicMock()
    mock_hit.score = 0.90
    mock_hit.payload = {"subject_id": "VIP_001"}
    mock_qdrant.search.return_value = [mock_hit]
    
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    res = module.process(dummy_crop, face_analysis_enabled=True)
    
    assert res is not None
    assert res.matched is True
    assert res.subject_id == "VIP_001"
    assert res.confidence == 0.90

def test_pipeline_unknown_face():
    module = FaceModule(match_threshold=0.8)
    
    mock_app = MagicMock()
    module.app = mock_app
    mock_face = MagicMock()
    mock_face.bbox = [0, 0, 100, 100]
    mock_face.normed_embedding = np.random.rand(512).astype(np.float32)
    mock_app.get.return_value = [mock_face]
    
    mock_qdrant = MagicMock()
    module.qdrant_client = mock_qdrant
    mock_hit = MagicMock()
    mock_hit.score = 0.50 # below threshold
    mock_qdrant.search.return_value = [mock_hit]
    
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    res = module.process(dummy_crop, face_analysis_enabled=True)
    
    assert res is not None
    assert res.matched is False
    assert res.subject_id is None

def test_pipeline_no_face():
    module = FaceModule()
    
    mock_app = MagicMock()
    module.app = mock_app
    mock_app.get.return_value = [] # no faces detected
    
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    res = module.process(dummy_crop, face_analysis_enabled=True)
    
    assert res is None

def test_pipeline_low_quality_face():
    module = FaceModule()
    
    mock_app = MagicMock()
    module.app = mock_app
    mock_face = MagicMock()
    mock_face.bbox = [0, 0, 100, 100]
    mock_face.normed_embedding = None # InsightFace failed to extract embedding due to blur
    mock_app.get.return_value = [mock_face]
    
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    res = module.process(dummy_crop, face_analysis_enabled=True)
    
    assert res is None

def test_pipeline_qdrant_unavailable():
    module = FaceModule()
    
    mock_app = MagicMock()
    module.app = mock_app
    mock_face = MagicMock()
    mock_face.bbox = [0, 0, 100, 100]
    mock_face.normed_embedding = np.random.rand(512).astype(np.float32)
    mock_app.get.return_value = [mock_face]
    
    mock_qdrant = MagicMock()
    module.qdrant_client = mock_qdrant
    mock_qdrant.search.side_effect = Exception("Connection Refused")
    
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    res = module.process(dummy_crop, face_analysis_enabled=True)
    
    assert res is not None
    assert res.matched is False # degraded gracefully
    assert res.subject_id is None
