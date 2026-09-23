import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
import numpy as np
from fastapi import FastAPI
from app.api.v1.faces import router, get_db

app = FastAPI()
app.include_router(router, prefix="/watchlists/faces")

@pytest.fixture
def mock_db():
    db = AsyncMock()
    
    # Mock refresh
    async def mock_refresh(instance):
        instance.id = 1
        from datetime import datetime
        instance.created_at = datetime.utcnow()
    db.refresh = AsyncMock(side_effect=mock_refresh)
    
    mock_result = MagicMock()
    
    mock_entry = MagicMock()
    mock_entry.id = 1
    mock_entry.type = "FACE"
    mock_entry.label = "John Doe"
    mock_entry.reference = "Emp-001"
    mock_entry.enabled = True
    mock_entry.threshold = 0.6
    mock_entry.created_at = "2024-01-01T00:00:00Z"
    
    mock_result.scalars().all.return_value = [mock_entry]
    mock_result.scalar_one_or_none.return_value = mock_entry
    db.execute.return_value = mock_result
    return db

@patch("app.api.v1.faces.face_service.process_image")
@patch("app.api.v1.faces.qdrant_service.upsert_face")
@patch("app.api.v1.faces.qdrant_service.create_collections")
def test_enroll_face(mock_create, mock_upsert, mock_process_image, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    mock_process_image.return_value = np.array([0.1, 0.2, 0.3])
    
    client = TestClient(app)
    
    response = client.post(
        "/watchlists/faces/",
        data={"label": "Test User", "reference": "ID-123"},
        files={"file": ("test.jpg", b"fake_image_bytes", "image/jpeg")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "Test User"
    assert data["reference"] == "ID-123"
    assert "embedding" not in data
    assert "vector" not in data
    
    mock_process_image.assert_called_once_with(b"fake_image_bytes")
    mock_upsert.assert_called_once()
    mock_create.assert_called_once()
    app.dependency_overrides.clear()
    
def test_list_faces(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    
    response = client.get("/watchlists/faces/")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 1
    assert data[0]["label"] == "John Doe"
    assert "embedding" not in data[0]
    app.dependency_overrides.clear()

@patch("app.api.v1.faces.qdrant_service.delete_face")
def test_delete_face(mock_delete, mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    
    response = client.delete("/watchlists/faces/1")
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    mock_db.delete.assert_called_once()
    mock_delete.assert_called_once_with("1")
    app.dependency_overrides.clear()
