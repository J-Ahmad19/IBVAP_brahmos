import numpy as np
import pytest
from unittest.mock import MagicMock
from app.models.face import FaceModule, FaceMatch

def test_face_module_disabled():
    module = FaceModule()
    
    # Process with face_analysis_enabled = False
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    res = module.process(dummy_crop, face_analysis_enabled=False)
    
    assert res is None


def test_face_module_pipeline_mocked():
    module = FaceModule()
    
    # Mock InsightFace
    mock_app = MagicMock()
    module.app = mock_app
    
    # Mock a detected face
    mock_face = MagicMock()
    mock_face.bbox = [10.0, 10.0, 50.0, 50.0]
    # Synthetic embedding (512-d)
    mock_face.normed_embedding = np.random.rand(512).astype(np.float32)
    
    mock_app.get.return_value = [mock_face]
    
    # Mock Qdrant Client
    mock_qdrant = MagicMock()
    module.qdrant_client = mock_qdrant
    
    mock_hit = MagicMock()
    mock_hit.score = 0.85
    mock_hit.payload = {"subject_id": "watch_001"}
    mock_qdrant.search.return_value = [mock_hit]
    
    # Run process
    dummy_crop = np.zeros((100, 100, 3), dtype=np.uint8)
    res = module.process(dummy_crop, face_analysis_enabled=True)
    
    assert isinstance(res, FaceMatch)
    assert res.matched is True
    assert res.subject_id == "watch_001"
    assert res.confidence == 0.85
    assert res.bbox == (10, 10, 50, 50)
    
    # Verify qdrant was called with normalized embedding
    mock_qdrant.search.assert_called_once()
    call_args = mock_qdrant.search.call_args[1]
    assert call_args["collection_name"] == "watchlist"
    assert "query_vector" in call_args
    assert len(call_args["query_vector"]) == 512

def test_normalize_embedding():
    module = FaceModule()
    
    # Non-zero embedding
    emb = np.array([3.0, 4.0])
    normed = module.normalize_embedding(emb)
    assert np.allclose(normed, np.array([0.6, 0.8]))
    
    # Zero embedding
    zero_emb = np.array([0.0, 0.0])
    zero_normed = module.normalize_embedding(zero_emb)
    assert np.allclose(zero_normed, zero_emb)

def test_search_watchlist_no_match():
    module = FaceModule(match_threshold=0.9)
    
    mock_qdrant = MagicMock()
    module.qdrant_client = mock_qdrant
    
    # Hit score is below threshold
    mock_hit = MagicMock()
    mock_hit.score = 0.5
    mock_qdrant.search.return_value = [mock_hit]
    
    emb = np.random.rand(512).astype(np.float32)
    matched, subject_id, conf = module.search_watchlist(emb)
    
    assert matched is False
    assert subject_id is None
    assert conf == 0.0
