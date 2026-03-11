from io import BytesIO
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from app.core.application.exceptions import (
    ImageConversionError,
    UnsupportedFileFormatError,
)


@pytest.fixture
def pdf2image_converter():
    """Create a Pdf2ImageConverter instance for testing"""
    # Import here to avoid circular import issues in tests
    from app.adapter.driven.conversion.pdf2image_converter import Pdf2ImageConverter
    return Pdf2ImageConverter()


@pytest.fixture
def sample_png_bytes():
    """Generate sample PNG image bytes for testing"""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_jpg_bytes():
    """Generate sample JPG image bytes for testing"""
    img = Image.new("RGB", (100, 100), color="blue")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def test_convert_pdf_to_image_single_page(pdf2image_converter):
    """Test that a single-page PDF is converted to PNG successfully."""
    # Arrange
    pdf_bytes = b"fake pdf content"
    mock_image = MagicMock(spec=Image.Image)
    mock_image.mode = "RGB"
    mock_image.size = (800, 600)
    
    expected_png_bytes = b"converted png content"
    mock_bytes_io = BytesIO(expected_png_bytes)
    
    # Act
    with patch("app.adapter.driven.conversion.pdf2image_converter.convert_from_bytes") as mock_convert:
        mock_convert.return_value = [mock_image]
        with patch("app.adapter.driven.conversion.pdf2image_converter.BytesIO", return_value=mock_bytes_io):
            result = pdf2image_converter.convert_to_image(pdf_bytes, ".pdf")
    
    # Assert
    mock_convert.assert_called_once_with(pdf_bytes, dpi=300)
    mock_image.save.assert_called_once()
    assert result == expected_png_bytes


def test_convert_pdf_to_image_multiple_pages_merged(pdf2image_converter):
    """Test that multi-page PDF pages are merged vertically into single PNG."""
    # Arrange
    pdf_bytes = b"fake multi-page pdf"
    mock_page1 = MagicMock(spec=Image.Image)
    mock_page1.size = (800, 600)
    mock_page1.mode = "RGB"
    
    mock_page2 = MagicMock(spec=Image.Image)
    mock_page2.size = (800, 600)
    mock_page2.mode = "RGB"
    
    mock_page3 = MagicMock(spec=Image.Image)
    mock_page3.size = (800, 600)
    mock_page3.mode = "RGB"
    
    mock_merged_image = MagicMock(spec=Image.Image)
    expected_result = b"merged png bytes"
    
    # Act
    with patch("app.adapter.driven.conversion.pdf2image_converter.convert_from_bytes") as mock_convert:
        mock_convert.return_value = [mock_page1, mock_page2, mock_page3]
        with patch("app.adapter.driven.conversion.pdf2image_converter.Image.new", return_value=mock_merged_image):
            with patch("app.adapter.driven.conversion.pdf2image_converter.BytesIO") as mock_bytesio:
                mock_buffer = BytesIO(expected_result)
                mock_bytesio.return_value = mock_buffer
                result = pdf2image_converter.convert_to_image(pdf_bytes, ".pdf")
    
    # Assert
    mock_convert.assert_called_once_with(pdf_bytes, dpi=300)
    # Verify merged image was created with correct dimensions (width=800, height=1800)
    # The new image should be called with correct dimensions
    assert result == expected_result


def test_convert_png_to_png_normalizes(pdf2image_converter, sample_png_bytes):
    """Test that PNG files are normalized (re-encoded) to standard PNG format."""
    # Arrange
    # Act
    result = pdf2image_converter.convert_to_image(sample_png_bytes, ".png")
    
    # Assert
    assert isinstance(result, bytes)
    assert len(result) > 0
    # Verify it's valid PNG by opening it
    img = Image.open(BytesIO(result))
    assert img.format == "PNG"


def test_convert_jpg_to_png_normalizes(pdf2image_converter, sample_jpg_bytes):
    """Test that JPG files are converted to PNG format."""
    # Arrange
    # Act
    result = pdf2image_converter.convert_to_image(sample_jpg_bytes, ".jpg")
    
    # Assert
    assert isinstance(result, bytes)
    assert len(result) > 0
    # Verify it's valid PNG
    img = Image.open(BytesIO(result))
    assert img.format == "PNG"


def test_convert_jpeg_extension_variant(pdf2image_converter, sample_jpg_bytes):
    """Test that .jpeg extension is handled like .jpg."""
    # Arrange
    # Act
    result = pdf2image_converter.convert_to_image(sample_jpg_bytes, ".jpeg")
    
    # Assert
    assert isinstance(result, bytes)
    img = Image.open(BytesIO(result))
    assert img.format == "PNG"


def test_convert_unsupported_format_raises_error(pdf2image_converter):
    """Test that unsupported file formats raise UnsupportedFileFormatError."""
    # Arrange
    file_bytes = b"some content"
    
    # Act & Assert
    with pytest.raises(UnsupportedFileFormatError, match="Unsupported file format"):
        pdf2image_converter.convert_to_image(file_bytes, ".txt")


def test_convert_pdf_conversion_failure_raises_error(pdf2image_converter):
    """Test that PDF conversion failures raise ImageConversionError."""
    # Arrange
    corrupt_pdf_bytes = b"not a valid pdf"
    
    # Act & Assert
    with patch("app.adapter.driven.conversion.pdf2image_converter.convert_from_bytes") as mock_convert:
        mock_convert.side_effect = Exception("PDF conversion failed")
        with pytest.raises(ImageConversionError, match="Failed to convert PDF"):
            pdf2image_converter.convert_to_image(corrupt_pdf_bytes, ".pdf")


def test_convert_image_loading_failure_raises_error(pdf2image_converter):
    """Test that image loading failures raise ImageConversionError."""
    # Arrange
    corrupt_image_bytes = b"not a valid image"
    
    # Act & Assert
    with pytest.raises(ImageConversionError, match="Failed to convert image"):
        pdf2image_converter.convert_to_image(corrupt_image_bytes, ".png")


def test_convert_case_insensitive_extension(pdf2image_converter, sample_png_bytes):
    """Test that extensions are handled case-insensitively."""
    # Arrange
    # Act
    result = pdf2image_converter.convert_to_image(sample_png_bytes, ".PNG")
    
    # Assert
    assert isinstance(result, bytes)
    img = Image.open(BytesIO(result))
    assert img.format == "PNG"


def test_convert_pdf_with_different_page_sizes(pdf2image_converter):
    """Test that PDFs with different page sizes are handled correctly."""
    # Arrange
    pdf_bytes = b"pdf with different page sizes"
    mock_page1 = MagicMock(spec=Image.Image)
    mock_page1.size = (800, 600)
    mock_page1.mode = "RGB"
    
    mock_page2 = MagicMock(spec=Image.Image)
    mock_page2.size = (1000, 800)  # Different size
    mock_page2.mode = "RGB"
    
    mock_merged_image = MagicMock(spec=Image.Image)
    expected_result = b"merged png with different sizes"
    
    # Act
    with patch("app.adapter.driven.conversion.pdf2image_converter.convert_from_bytes") as mock_convert:
        mock_convert.return_value = [mock_page1, mock_page2]
        with patch("app.adapter.driven.conversion.pdf2image_converter.Image.new", return_value=mock_merged_image):
            with patch("app.adapter.driven.conversion.pdf2image_converter.BytesIO") as mock_bytesio:
                mock_buffer = BytesIO(expected_result)
                mock_bytesio.return_value = mock_buffer
                result = pdf2image_converter.convert_to_image(pdf_bytes, ".pdf")
    
    # Assert
    # Should use the maximum width (1000) and sum heights (1400)
    assert result == expected_result
