import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from minio.error import S3Error

from app.services.minio_wrapper import MinIOService
from app.core.config import settings


@pytest.fixture
def mock_minio_client():
    with patch('app.services.minio_wrapper.Minio') as MockMinio:
        client_instance = MockMinio.return_value
        yield client_instance


@pytest.fixture
def minio_service(mock_minio_client):
    return MinIOService()


def test_health_check_success(minio_service, mock_minio_client):
    mock_minio_client.bucket_exists.return_value = True
    assert minio_service.health_check() is True
    mock_minio_client.bucket_exists.assert_called_once_with(settings.MINIO_EVIDENCE_BUCKET)


def test_health_check_failure(minio_service, mock_minio_client):
    mock_minio_client.bucket_exists.side_effect = Exception("Connection refused")
    assert minio_service.health_check() is False


@patch('app.services.minio_wrapper.datetime')
def test_generate_object_path(mock_datetime, minio_service):
    # Mock current time
    mock_now = datetime(2026, 12, 1, 15, 30, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    path = minio_service._generate_object_path("cam-1", "evt-123", "snapshot.jpg")
    assert path == "alerts/cam-1/2026/12/01/evt-123/snapshot.jpg"


@patch('app.services.minio_wrapper.datetime')
def test_upload_snapshot(mock_datetime, minio_service, mock_minio_client):
    mock_now = datetime(2026, 12, 1, 15, 30, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    image_bytes = b"mock_image_data"
    
    media_ref = minio_service.upload_snapshot("cam-1", "evt-123", image_bytes)
    
    expected_path = "alerts/cam-1/2026/12/01/evt-123/snapshot.jpg"
    expected_ref = f"s3://{settings.MINIO_EVIDENCE_BUCKET}/{expected_path}"
    
    assert media_ref == expected_ref
    mock_minio_client.put_object.assert_called_once()
    
    call_args = mock_minio_client.put_object.call_args[1]
    # Check that we passed the correct bucket and path (using args tuple)
    args = mock_minio_client.put_object.call_args[0]
    assert args[0] == settings.MINIO_EVIDENCE_BUCKET
    assert args[1] == expected_path
    
    assert call_args['length'] == len(image_bytes)
    assert call_args['content_type'] == "image/jpeg"


@patch('app.services.minio_wrapper.datetime')
def test_upload_clip(mock_datetime, minio_service, mock_minio_client):
    mock_now = datetime(2026, 12, 1, 15, 30, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    video_bytes = b"mock_video_data"
    
    media_ref = minio_service.upload_clip("cam-1", "evt-123", video_bytes)
    
    expected_path = "alerts/cam-1/2026/12/01/evt-123/clip.mp4"
    expected_ref = f"s3://{settings.MINIO_EVIDENCE_BUCKET}/{expected_path}"
    
    assert media_ref == expected_ref
    mock_minio_client.put_object.assert_called_once()
    
    args = mock_minio_client.put_object.call_args[0]
    call_args = mock_minio_client.put_object.call_args[1]
    
    assert args[0] == settings.MINIO_EVIDENCE_BUCKET
    assert args[1] == expected_path
    assert call_args['length'] == len(video_bytes)
    assert call_args['content_type'] == "video/mp4"


def test_get_presigned_url_valid(minio_service, mock_minio_client):
    mock_minio_client.presigned_get_object.return_value = "http://localhost:9000/presigned-url"
    
    media_ref = f"s3://{settings.MINIO_EVIDENCE_BUCKET}/alerts/cam-1/2026/12/01/evt-123/snapshot.jpg"
    
    url = minio_service.get_presigned_url(media_ref)
    
    assert url == "http://localhost:9000/presigned-url"
    mock_minio_client.presigned_get_object.assert_called_once()


def test_get_presigned_url_invalid(minio_service):
    media_ref = "s3://wrong-bucket/alerts/cam-1/snapshot.jpg"
    
    with pytest.raises(ValueError, match="Invalid media_ref format"):
        minio_service.get_presigned_url(media_ref)


def test_delete_evidence_valid(minio_service, mock_minio_client):
    media_ref = f"s3://{settings.MINIO_EVIDENCE_BUCKET}/alerts/cam-1/2026/12/01/evt-123/snapshot.jpg"
    
    result = minio_service.delete_evidence(media_ref)
    
    assert result is True
    mock_minio_client.remove_object.assert_called_once_with(
        settings.MINIO_EVIDENCE_BUCKET,
        "alerts/cam-1/2026/12/01/evt-123/snapshot.jpg"
    )


def test_delete_evidence_invalid(minio_service):
    media_ref = "invalid-format://foo/bar"
    
    with pytest.raises(ValueError, match="Invalid media_ref format"):
        minio_service.delete_evidence(media_ref)


def test_delete_evidence_s3_error(minio_service, mock_minio_client):
    media_ref = f"s3://{settings.MINIO_EVIDENCE_BUCKET}/alerts/cam-1/2026/12/01/evt-123/snapshot.jpg"
    
    # Mock an S3 error
    mock_minio_client.remove_object.side_effect = S3Error(
        code="NoSuchKey", message="Object not found",
        resource="/alerts/cam-1/...", request_id="123",
        host_id="123", response=MagicMock()
    )
    
    result = minio_service.delete_evidence(media_ref)
    assert result is False
