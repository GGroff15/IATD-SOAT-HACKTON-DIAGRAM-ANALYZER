from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.adapter.driven.persistence.s3_file_storage import S3FileStorage
from app.core.application.exceptions import FileNotFoundError, FileStorageError


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing."""
    client = MagicMock()
    client.get = AsyncMock()
    return client


@pytest.fixture
def s3_storage(mock_http_client):
    """S3FileStorage instance with mocked HTTP client."""
    return S3FileStorage(http_client=mock_http_client)


@pytest.mark.asyncio
async def test_download_file_success(s3_storage, mock_http_client):
    """Test successful file download."""
    # Arrange
    file_url = "https://example.com/test-folder/test-file.pdf"
    expected_content = b"file content"
    request = httpx.Request("GET", file_url)
    mock_http_client.get.return_value = httpx.Response(
        200,
        content=expected_content,
        request=request,
    )

    # Act
    result = await s3_storage.download_file(file_url=file_url)

    # Assert
    assert result == expected_content
    mock_http_client.get.assert_awaited_once_with(file_url)


@pytest.mark.asyncio
async def test_download_file_not_found(s3_storage, mock_http_client):
    """Test file not found raises FileNotFoundError."""
    # Arrange
    file_url = "https://example.com/test-folder/missing-file.pdf"
    request = httpx.Request("GET", file_url)
    mock_http_client.get.return_value = httpx.Response(404, request=request)

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="not found"):
        await s3_storage.download_file(file_url=file_url)


@pytest.mark.asyncio
async def test_download_file_http_error(s3_storage, mock_http_client):
    """Test non-404 HTTP errors raise FileStorageError."""
    # Arrange
    file_url = "https://example.com/test-folder/test-file.pdf"
    request = httpx.Request("GET", file_url)
    mock_http_client.get.return_value = httpx.Response(403, request=request)

    # Act & Assert
    with pytest.raises(FileStorageError, match="HTTP 403"):
        await s3_storage.download_file(file_url=file_url)


@pytest.mark.asyncio
async def test_download_file_request_error(s3_storage, mock_http_client):
    """Test request errors raise FileStorageError."""
    # Arrange
    file_url = "https://example.com/test-folder/test-file.pdf"
    request = httpx.Request("GET", file_url)
    mock_http_client.get.side_effect = httpx.RequestError("network error", request=request)

    # Act & Assert
    with pytest.raises(FileStorageError, match="network error"):
        await s3_storage.download_file(file_url=file_url)


@pytest.mark.asyncio
async def test_download_file_rejects_non_http_url(s3_storage):
    """Test non-http(s) URLs are rejected with explicit storage error."""
    with pytest.raises(FileStorageError, match="Only http\(s\) URLs are supported"):
        await s3_storage.download_file(file_url="s3://example-bucket/test.pdf")
