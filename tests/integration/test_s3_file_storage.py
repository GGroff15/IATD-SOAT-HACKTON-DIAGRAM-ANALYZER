import httpx
import pytest

from app.adapter.driven.persistence.s3_file_storage import S3FileStorage
from app.core.application.exceptions import FileNotFoundError, FileStorageError


def _create_test_bucket(s3_client, bucket_name: str) -> None:
    """Create a bucket that is compatible with region-specific endpoints."""
    region = s3_client.meta.region_name or "us-east-1"
    if region == "us-east-1":
        s3_client.create_bucket(Bucket=bucket_name)
        return
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": region},
    )


def _build_object_url(s3_client, bucket_name: str, object_key: str) -> str:
    base_url = s3_client.meta.endpoint_url.rstrip("/")
    return f"{base_url}/{bucket_name}/{object_key}"


@pytest.mark.asyncio
async def test_s3_download_file_success(s3_client, test_bucket):
    """Integration test: successfully download a file from S3"""
    # Arrange - create bucket and upload file
    _create_test_bucket(s3_client, test_bucket)
    test_content = b"test diagram content"
    s3_client.put_object(
        Bucket=test_bucket,
        Key="folder-123/diagram-456.pdf",
        Body=test_content
    )

    file_url = _build_object_url(
        s3_client,
        test_bucket,
        "folder-123/diagram-456.pdf",
    )

    async with httpx.AsyncClient(follow_redirects=True) as http_client:
        storage = S3FileStorage(http_client=http_client)

        # Act
        result = await storage.download_file(file_url=file_url)

    # Assert
    assert result == test_content


@pytest.mark.asyncio
async def test_s3_download_file_not_found(s3_client, test_bucket):
    """Integration test: download non-existent file raises FileNotFoundError"""
    # Arrange - create empty bucket
    _create_test_bucket(s3_client, test_bucket)

    file_url = _build_object_url(
        s3_client,
        test_bucket,
        "missing-folder/missing-file.pdf",
    )

    async with httpx.AsyncClient(follow_redirects=True) as http_client:
        storage = S3FileStorage(http_client=http_client)

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="not found"):
            await storage.download_file(file_url=file_url)


@pytest.mark.asyncio
async def test_s3_download_file_with_different_extensions(s3_client, test_bucket):
    """Integration test: download files with different extensions"""
    # Arrange
    _create_test_bucket(s3_client, test_bucket)

    test_files = [
        ("folder/file1.pdf", b"pdf content"),
        ("folder/file2.png", b"png content"),
        ("folder/file3.jpg", b"jpg content"),
    ]
    
    for key, content in test_files:
        s3_client.put_object(Bucket=test_bucket, Key=key, Body=content)

    async with httpx.AsyncClient(follow_redirects=True) as http_client:
        storage = S3FileStorage(http_client=http_client)

        # Act & Assert
        result_pdf = await storage.download_file(
            file_url=_build_object_url(s3_client, test_bucket, "folder/file1.pdf")
        )
        assert result_pdf == b"pdf content"

        result_png = await storage.download_file(
            file_url=_build_object_url(s3_client, test_bucket, "folder/file2.png")
        )
        assert result_png == b"png content"

        result_jpg = await storage.download_file(
            file_url=_build_object_url(s3_client, test_bucket, "folder/file3.jpg")
        )
        assert result_jpg == b"jpg content"


@pytest.mark.asyncio
async def test_s3_download_file_with_nested_folders(s3_client, test_bucket):
    """Integration test: download file from nested folder structure"""
    # Arrange
    _create_test_bucket(s3_client, test_bucket)
    test_content = b"nested content"
    s3_client.put_object(
        Bucket=test_bucket,
        Key="level1/level2/level3/diagram.pdf",
        Body=test_content
    )

    file_url = _build_object_url(
        s3_client,
        test_bucket,
        "level1/level2/level3/diagram.pdf",
    )

    async with httpx.AsyncClient(follow_redirects=True) as http_client:
        storage = S3FileStorage(http_client=http_client)

        # Act
        result = await storage.download_file(file_url=file_url)

    # Assert
    assert result == test_content


@pytest.mark.asyncio
async def test_s3_download_file_bucket_not_exists(s3_client):
    """Integration test: download from non-existent bucket raises FileNotFoundError"""
    # Arrange - don't create the bucket
    file_url = _build_object_url(
        s3_client,
        "non-existent-bucket",
        "folder/file.pdf",
    )

    async with httpx.AsyncClient(follow_redirects=True) as http_client:
        storage = S3FileStorage(http_client=http_client)

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="not found"):
            await storage.download_file(file_url=file_url)


@pytest.mark.asyncio
async def test_s3_download_file_rejects_non_http_uri(s3_client, test_bucket):
    """Integration test: non-http(s) URI fails with explicit validation error."""
    _create_test_bucket(s3_client, test_bucket)
    async with httpx.AsyncClient(follow_redirects=True) as http_client:
        storage = S3FileStorage(http_client=http_client)

        with pytest.raises(FileStorageError, match="Only http\(s\) URLs are supported"):
            await storage.download_file(file_url="s3://example-bucket/diagram.pdf")
