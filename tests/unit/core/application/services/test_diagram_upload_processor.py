from unittest.mock import AsyncMock, Mock
from uuid import uuid4
import pytest

from app.core.domain.entities.diagram_upload import DiagramUpload
from app.core.application.services.diagram_upload_processor import DiagramUploadProcessor
from app.core.application.exceptions import ImageConversionError


class MockFileStorage:
    """Mock file storage for testing"""
    def __init__(self):
        self.download_file = AsyncMock(return_value=b"mock file content")


class MockImageConverter:
    """Mock image converter for testing"""
    def __init__(self):
        self.convert_to_image = Mock(return_value=b"converted png content")


@pytest.mark.asyncio
async def test_processor_downloads_file():
    """Test that processor calls file storage to download the file"""
    # Arrange
    upload = DiagramUpload(uuid4(), "folder-x", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter
    )
    
    # Act
    await processor.process(upload)
    
    # Assert
    mock_storage.download_file.assert_called_once_with(
        folder="folder-x",
        filename=str(upload.diagram_upload_id),
        extension=".pdf"
    )


@pytest.mark.asyncio
async def test_processor_with_custom_extension():
    """Test that processor uses the correct extension"""
    # Arrange
    upload = DiagramUpload(uuid4(), "my-folder", extension=".png")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter
    )
    
    # Act
    await processor.process(upload)
    
    # Assert
    mock_storage.download_file.assert_called_once_with(
        folder="my-folder",
        filename=str(upload.diagram_upload_id),
        extension=".png"
    )


@pytest.mark.asyncio
async def test_processor_converts_file_after_download():
    """Test that processor calls image converter after downloading file"""
    # Arrange
    upload = DiagramUpload(uuid4(), "test-folder", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_storage.download_file.return_value = b"original pdf content"
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.return_value = b"converted png bytes"
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter
    )
    
    # Act
    await processor.process(upload)
    
    # Assert
    mock_converter.convert_to_image.assert_called_once_with(
        file_content=b"original pdf content",
        extension=".pdf"
    )


@pytest.mark.asyncio
async def test_processor_handles_conversion_error():
    """Test that processor handles image conversion errors gracefully"""
    # Arrange
    upload = DiagramUpload(uuid4(), "test-folder", extension=".pdf")
    mock_storage = MockFileStorage()
    mock_converter = MockImageConverter()
    mock_converter.convert_to_image.side_effect = ImageConversionError("Conversion failed")
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter
    )
    
    # Act & Assert
    with pytest.raises(ImageConversionError, match="Conversion failed"):
        await processor.process(upload)


@pytest.mark.asyncio
async def test_processor_with_jpg_extension():
    """Test that processor handles JPG files correctly"""
    # Arrange
    upload = DiagramUpload(uuid4(), "images", extension=".jpg")
    mock_storage = MockFileStorage()
    mock_storage.download_file.return_value = b"jpg image content"
    mock_converter = MockImageConverter()
    processor = DiagramUploadProcessor(
        file_storage=mock_storage,
        image_converter=mock_converter
    )
    
    # Act
    await processor.process(upload)
    
    # Assert
    mock_converter.convert_to_image.assert_called_once_with(
        file_content=b"jpg image content",
        extension=".jpg"
    )
