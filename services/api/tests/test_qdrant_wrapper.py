import pytest
from unittest.mock import MagicMock, patch
from qdrant_client.http.models import PointStruct, VectorParams, Distance

from app.services.qdrant_wrapper import QdrantService
from app.core.config import settings

@pytest.fixture
def mock_qdrant_client():
    with patch('app.services.qdrant_wrapper.QdrantClient') as MockClient:
        # Mock instance
        client_instance = MockClient.return_value
        yield client_instance

@pytest.fixture
def qdrant_service(mock_qdrant_client):
    # Setting host and port explicitly to avoid real connection attempts if config changes
    return QdrantService(host="mock_host", port=1234)


def test_health_check_success(qdrant_service, mock_qdrant_client):
    mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
    assert qdrant_service.health_check() is True
    mock_qdrant_client.get_collections.assert_called_once()


def test_health_check_failure(qdrant_service, mock_qdrant_client):
    mock_qdrant_client.get_collections.side_effect = Exception("Connection refused")
    assert qdrant_service.health_check() is False


def test_create_collections(qdrant_service, mock_qdrant_client):
    # Mock that no collections exist
    mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
    
    qdrant_service.create_collections()
    
    # Should be called twice (face and plate)
    assert mock_qdrant_client.create_collection.call_count == 2
    
    # Verify first call is for face_watchlist with correct params
    call_args_face = mock_qdrant_client.create_collection.call_args_list[0][1]
    assert call_args_face['collection_name'] == 'face_watchlist'
    assert call_args_face['vectors_config'].size == settings.FACE_VECTOR_SIZE
    assert call_args_face['vectors_config'].distance == Distance.COSINE
    
    # Verify second call is for plate_watchlist
    call_args_plate = mock_qdrant_client.create_collection.call_args_list[1][1]
    assert call_args_plate['collection_name'] == 'plate_watchlist'
    assert call_args_plate['vectors_config'].size == settings.PLATE_VECTOR_SIZE


def test_delete_collection(qdrant_service, mock_qdrant_client):
    qdrant_service.delete_collection("test_col")
    mock_qdrant_client.delete_collection.assert_called_once_with(collection_name="test_col")


def test_upsert_face_valid(qdrant_service, mock_qdrant_client):
    vector_id = "f-123"
    vector = [0.1] * settings.FACE_VECTOR_SIZE
    payload = {"person_id": "p-1"}
    
    qdrant_service.upsert_face(vector_id, vector, payload)
    
    mock_qdrant_client.upsert.assert_called_once()
    call_args = mock_qdrant_client.upsert.call_args[1]
    assert call_args['collection_name'] == 'face_watchlist'
    
    point = call_args['points'][0]
    assert isinstance(point, PointStruct)
    assert point.id == vector_id
    assert point.vector == vector
    assert point.payload == payload


def test_upsert_face_invalid_dimension(qdrant_service):
    vector_id = "f-123"
    vector = [0.1] * (settings.FACE_VECTOR_SIZE - 1)  # Invalid size
    
    with pytest.raises(ValueError, match="does not match face config"):
        qdrant_service.upsert_face(vector_id, vector)


def test_search_face(qdrant_service, mock_qdrant_client):
    vector = [0.1] * settings.FACE_VECTOR_SIZE
    mock_qdrant_client.search.return_value = ["mock_result_1", "mock_result_2"]
    
    results = qdrant_service.search_face(vector, limit=2)
    
    assert len(results) == 2
    mock_qdrant_client.search.assert_called_once_with(
        collection_name='face_watchlist',
        query_vector=vector,
        limit=2,
        query_filter=None
    )


def test_delete_face(qdrant_service, mock_qdrant_client):
    vector_id = "f-123"
    qdrant_service.delete_face(vector_id)
    
    mock_qdrant_client.delete.assert_called_once_with(
        collection_name='face_watchlist',
        points_selector=[vector_id]
    )


# --- Plate Tests ---
# (They mirror the face tests but ensure the plate_collection and PLATE_VECTOR_SIZE are used)

def test_upsert_plate_valid(qdrant_service, mock_qdrant_client):
    vector_id = "pl-123"
    vector = [0.1] * settings.PLATE_VECTOR_SIZE
    payload = {"plate": "XYZ123"}
    
    qdrant_service.upsert_plate(vector_id, vector, payload)
    
    mock_qdrant_client.upsert.assert_called_once()
    assert mock_qdrant_client.upsert.call_args[1]['collection_name'] == 'plate_watchlist'


def test_upsert_plate_invalid_dimension(qdrant_service):
    vector_id = "pl-123"
    vector = [0.1] * (settings.PLATE_VECTOR_SIZE + 1)  # Invalid size
    
    with pytest.raises(ValueError, match="does not match plate config"):
        qdrant_service.upsert_plate(vector_id, vector)


def test_search_plate(qdrant_service, mock_qdrant_client):
    vector = [0.1] * settings.PLATE_VECTOR_SIZE
    
    qdrant_service.search_plate(vector, limit=1)
    
    mock_qdrant_client.search.assert_called_once_with(
        collection_name='plate_watchlist',
        query_vector=vector,
        limit=1,
        query_filter=None
    )

def test_delete_plate(qdrant_service, mock_qdrant_client):
    vector_id = "pl-123"
    qdrant_service.delete_plate(vector_id)
    
    mock_qdrant_client.delete.assert_called_once_with(
        collection_name='plate_watchlist',
        points_selector=[vector_id]
    )
