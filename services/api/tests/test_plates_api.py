import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from app.api.v1.plates import router, get_db

app = FastAPI()
app.include_router(router, prefix="/watchlists/plates")

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
    mock_entry.type = "PLATE"
    mock_entry.label = "MH12AB1234"
    mock_entry.reference = "Car-1"
    mock_entry.enabled = True
    mock_entry.threshold = None
    mock_entry.created_at = "2024-01-01T00:00:00Z"
    
    mock_result.scalars().all.return_value = [mock_entry]
    mock_result.scalars().first.return_value = None  # Default to no duplicate
    db.execute.return_value = mock_result
    return db

def test_create_plate(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    
    response = client.post(
        "/watchlists/plates",
        json={"type": "PLATE", "label": "DL1A1234", "enabled": True}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["label"] == "DL1A1234"
    
    app.dependency_overrides.clear()

def test_create_plate_duplicate(mock_db):
    # Setup mock to return an existing entry
    mock_result = MagicMock()
    mock_entry = MagicMock()
    mock_result.scalars().first.return_value = mock_entry
    mock_db.execute.return_value = mock_result
    
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    
    response = client.post(
        "/watchlists/plates",
        json={"type": "PLATE", "label": "MH12AB1234", "enabled": True}
    )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]
    app.dependency_overrides.clear()

def test_get_plates(mock_db):
    # Setup mock to return the list
    mock_result = MagicMock()
    mock_entry = MagicMock()
    mock_entry.id = 1
    mock_entry.type = "PLATE"
    mock_entry.label = "MH12AB1234"
    mock_entry.reference = "Car-1"
    mock_entry.enabled = True
    mock_entry.threshold = None
    mock_entry.created_at = "2024-01-01T00:00:00Z"
    mock_result.scalars().all.return_value = [mock_entry]
    mock_db.execute.return_value = mock_result
    
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    
    response = client.get("/watchlists/plates")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 1
    assert data[0]["label"] == "MH12AB1234"
    app.dependency_overrides.clear()

def test_delete_plate(mock_db):
    mock_result = MagicMock()
    mock_entry = MagicMock()
    mock_result.scalars().first.return_value = mock_entry
    mock_db.execute.return_value = mock_result
    
    app.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    
    response = client.delete("/watchlists/plates/1")
    
    assert response.status_code == 204
    
    mock_db.delete.assert_called_once()
    app.dependency_overrides.clear()
