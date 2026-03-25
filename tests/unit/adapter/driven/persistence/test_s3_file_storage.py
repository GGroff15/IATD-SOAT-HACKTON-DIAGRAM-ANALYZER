from unittest.mock import MagicMock
import pytest
from botocore.exceptions import ClientError

from app.adapter.driven.persistence.s3_file_storage import S3FileStorage
from app.core.application.exceptions import FileNotFoundError, FileStorageError


@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing"""
    return MagicMock()


@pytest.fixture
def s3_storage(mock_s3_client):
    """S3FileStorage instance with mocked client"""
    return S3FileStorage(s3_client=mock_s3_client, bucket_name="test-bucket")


@pytest.mark.asyncio
async def test_download_file_success(s3_storage, mock_s3_client):
    """Test successful file download"""
    # Arrange
    expected_content = b"file content"
    mock_response = {"Body": MagicMock()}
    mock_response["Body"].read = MagicMock(return_value=expected_content)
    mock_s3_client.get_object.return_value = mock_response
    
    # Act
    result = await s3_storage.download_file(file_url="s3://test-bucket/test-folder/test-file.pdf")
    
    # Assert
    assert result == expected_content
    mock_s3_client.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="test-folder/test-file.pdf"
    )


@pytest.mark.asyncio
async def test_download_file_not_found(s3_storage, mock_s3_client):
    """Test file not found raises FileNotFoundError"""
    # Arrange
    error_response = {"Error": {"Code": "NoSuchKey"}}
    mock_s3_client.get_object.side_effect = ClientError(
        error_response, "GetObject"
    )
    
    # Act & Assert
    with pytest.raises(FileNotFoundError, match="not found in bucket"):
        await s3_storage.download_file(file_url="s3://test-bucket/test-folder/missing-file.pdf")


@pytest.mark.asyncio
async def test_download_file_client_error(s3_storage, mock_s3_client):
    """Test other client errors raise FileStorageError"""
    # Arrange
    error_response = {"Error": {"Code": "AccessDenied"}}
    mock_s3_client.get_object.side_effect = ClientError(
        error_response, "GetObject"
    )
    
    # Act & Assert
    with pytest.raises(FileStorageError, match="Failed to download file"):
        await s3_storage.download_file(file_url="s3://test-bucket/test-folder/test-file.pdf")


@pytest.mark.asyncio
async def test_download_file_generic_exception(s3_storage, mock_s3_client):
    """Test generic exceptions raise FileStorageError"""
    # Arrange
    mock_s3_client.get_object.side_effect = Exception("Unexpected error")
    
    # Act & Assert
    with pytest.raises(FileStorageError, match="Unexpected error during file download"):
        await s3_storage.download_file(file_url="s3://test-bucket/test-folder/test-file.pdf")


@pytest.mark.asyncio
async def test_download_file_constructs_correct_key(s3_storage, mock_s3_client):
    """Test S3 key construction with different parameters"""
    # Arrange
    mock_response = {"Body": MagicMock()}
    mock_response["Body"].read = MagicMock(return_value=b"content")
    mock_s3_client.get_object.return_value = mock_response
    
    # Act
    await s3_storage.download_file(file_url="s3://test-bucket/my-folder/subfolder/diagram-123.png")
    
    # Assert
    mock_s3_client.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="my-folder/subfolder/diagram-123.png"
    )


@pytest.mark.asyncio
async def test_download_file_rejects_non_s3_uri(s3_storage):
    """Test non-S3 URIs are rejected with explicit storage error."""
    with pytest.raises(FileStorageError, match="Only s3:// URIs are supported"):
        await s3_storage.download_file(file_url="https://example.com/test.pdf")
