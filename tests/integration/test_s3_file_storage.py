import pytest

from app.adapter.driven.persistence.s3_file_storage import S3FileStorage
from app.core.application.exceptions import FileNotFoundError, FileStorageError


@pytest.mark.asyncio
async def test_s3_download_file_success(s3_client, test_bucket):
    """Integration test: successfully download a file from S3"""
    # Arrange - create bucket and upload file
    s3_client.create_bucket(Bucket=test_bucket)
    test_content = b"test diagram content"
    s3_client.put_object(
        Bucket=test_bucket,
        Key="folder-123/diagram-456.pdf",
        Body=test_content
    )
    
    storage = S3FileStorage(s3_client=s3_client, bucket_name=test_bucket)
    
    # Act
    result = await storage.download_file(
        folder="folder-123",
        filename="diagram-456",
        extension=".pdf"
    )
    
    # Assert
    assert result == test_content


@pytest.mark.asyncio
async def test_s3_download_file_not_found(s3_client, test_bucket):
    """Integration test: download non-existent file raises FileNotFoundError"""
    # Arrange - create empty bucket
    s3_client.create_bucket(Bucket=test_bucket)
    storage = S3FileStorage(s3_client=s3_client, bucket_name=test_bucket)
    
    # Act & Assert
    with pytest.raises(FileNotFoundError, match="not found in bucket"):
        await storage.download_file(
            folder="missing-folder",
            filename="missing-file",
            extension=".pdf"
        )


@pytest.mark.asyncio
async def test_s3_download_file_with_different_extensions(s3_client, test_bucket):
    """Integration test: download files with different extensions"""
    # Arrange
    s3_client.create_bucket(Bucket=test_bucket)
    storage = S3FileStorage(s3_client=s3_client, bucket_name=test_bucket)
    
    test_files = [
        ("folder/file1.pdf", b"pdf content"),
        ("folder/file2.png", b"png content"),
        ("folder/file3.jpg", b"jpg content"),
    ]
    
    for key, content in test_files:
        s3_client.put_object(Bucket=test_bucket, Key=key, Body=content)
    
    # Act & Assert
    result_pdf = await storage.download_file("folder", "file1", ".pdf")
    assert result_pdf == b"pdf content"
    
    result_png = await storage.download_file("folder", "file2", ".png")
    assert result_png == b"png content"
    
    result_jpg = await storage.download_file("folder", "file3", ".jpg")
    assert result_jpg == b"jpg content"


@pytest.mark.asyncio
async def test_s3_download_file_with_nested_folders(s3_client, test_bucket):
    """Integration test: download file from nested folder structure"""
    # Arrange
    s3_client.create_bucket(Bucket=test_bucket)
    storage = S3FileStorage(s3_client=s3_client, bucket_name=test_bucket)
    
    test_content = b"nested content"
    s3_client.put_object(
        Bucket=test_bucket,
        Key="level1/level2/level3/diagram.pdf",
        Body=test_content
    )
    
    # Act
    result = await storage.download_file(
        folder="level1/level2/level3",
        filename="diagram",
        extension=".pdf"
    )
    
    # Assert
    assert result == test_content


@pytest.mark.asyncio
async def test_s3_download_file_bucket_not_exists(s3_client):
    """Integration test: download from non-existent bucket raises FileStorageError"""
    # Arrange - don't create the bucket
    storage = S3FileStorage(s3_client=s3_client, bucket_name="non-existent-bucket")
    
    # Act & Assert
    with pytest.raises(FileStorageError, match="Failed to download file"):
        await storage.download_file(
            folder="folder",
            filename="file",
            extension=".pdf"
        )
