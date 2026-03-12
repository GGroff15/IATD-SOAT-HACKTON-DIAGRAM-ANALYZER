from io import BytesIO
from unittest.mock import MagicMock
import pytest
from botocore.exceptions import ClientError
from PIL import Image

from app.core.application.exceptions import TextExtractionError


@pytest.fixture
def mock_textract_client():
    """Mock AWS Textract client for testing"""
    return MagicMock()


@pytest.fixture
def sample_image_bytes():
    """Generate sample PNG image bytes for testing"""
    img = Image.new("RGB", (640, 480), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def textract_ocr(mock_textract_client):
    """TextractOCR instance with mocked client"""
    from app.adapter.driven.ocr.textract_ocr import TextractOCR
    return TextractOCR(textract_client=mock_textract_client)


def test_textract_ocr_extract_text_success(textract_ocr, mock_textract_client, sample_image_bytes):
    """Test successful text extraction from image region"""
    # Arrange
    mock_response = {
        "Blocks": [
            {
                "BlockType": "LINE",
                "Text": "Login Button",
                "Confidence": 99.5
            },
            {
                "BlockType": "LINE",
                "Text": "Click here to login",
                "Confidence": 98.2
            }
        ]
    }
    mock_textract_client.detect_document_text.return_value = mock_response
    
    # Act
    result = textract_ocr.extract_text(
        image_bytes=sample_image_bytes,
        x=100.0,
        y=200.0,
        width=150.0,
        height=50.0
    )
    
    # Assert
    assert result == "Login Button Click here to login"
    mock_textract_client.detect_document_text.assert_called_once()
    call_args = mock_textract_client.detect_document_text.call_args
    assert call_args[1]["Document"]["Bytes"] is not None


def test_textract_ocr_extract_text_no_text_found(textract_ocr, mock_textract_client, sample_image_bytes):
    """Test that empty string is returned when no text is detected"""
    # Arrange
    mock_response = {
        "Blocks": []
    }
    mock_textract_client.detect_document_text.return_value = mock_response
    
    # Act
    result = textract_ocr.extract_text(
        image_bytes=sample_image_bytes,
        x=10.0,
        y=20.0,
        width=100.0,
        height=30.0
    )
    
    # Assert
    assert result == ""


def test_textract_ocr_extract_text_only_line_blocks(textract_ocr, mock_textract_client, sample_image_bytes):
    """Test that only LINE blocks are extracted, not PAGE or WORD blocks"""
    # Arrange
    mock_response = {
        "Blocks": [
            {
                "BlockType": "PAGE",
                "Text": "This should be ignored",
                "Confidence": 99.0
            },
            {
                "BlockType": "LINE",
                "Text": "Submit",
                "Confidence": 97.5
            },
            {
                "BlockType": "WORD",
                "Text": "This should also be ignored",
                "Confidence": 95.0
            }
        ]
    }
    mock_textract_client.detect_document_text.return_value = mock_response
    
    # Act
    result = textract_ocr.extract_text(
        image_bytes=sample_image_bytes,
        x=50.0,
        y=75.0,
        width=200.0,
        height=40.0
    )
    
    # Assert
    assert result == "Submit"


def test_textract_ocr_extract_text_client_error(textract_ocr, mock_textract_client, sample_image_bytes):
    """Test that ClientError is mapped to TextExtractionError"""
    # Arrange
    error_response = {"Error": {"Code": "InvalidParameterException", "Message": "Invalid image"}}
    mock_textract_client.detect_document_text.side_effect = ClientError(
        error_response, "DetectDocumentText"
    )
    
    # Act & Assert
    with pytest.raises(TextExtractionError, match="Failed to extract text"):
        textract_ocr.extract_text(
            image_bytes=sample_image_bytes,
            x=100.0,
            y=200.0,
            width=50.0,
            height=50.0
        )


def test_textract_ocr_extract_text_generic_exception(textract_ocr, mock_textract_client, sample_image_bytes):
    """Test that generic exceptions are mapped to TextExtractionError"""
    # Arrange
    mock_textract_client.detect_document_text.side_effect = Exception("Unexpected error")
    
    # Act & Assert
    with pytest.raises(TextExtractionError, match="Failed to extract text"):
        textract_ocr.extract_text(
            image_bytes=sample_image_bytes,
            x=100.0,
            y=200.0,
            width=50.0,
            height=50.0
        )


def test_textract_ocr_crops_image_to_bounding_box(textract_ocr, mock_textract_client):
    """Test that image is cropped to the specified bounding box before OCR"""
    # Arrange
    # Create a larger image with known dimensions
    img = Image.new("RGB", (1000, 800), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    
    mock_response = {"Blocks": [{"BlockType": "LINE", "Text": "Test"}]}
    mock_textract_client.detect_document_text.return_value = mock_response
    
    # Act
    textract_ocr.extract_text(
        image_bytes=image_bytes,
        x=100.0,
        y=150.0,
        width=200.0,
        height=100.0
    )
    
    # Assert - verify Textract was called with cropped image bytes
    mock_textract_client.detect_document_text.assert_called_once()
    call_args = mock_textract_client.detect_document_text.call_args
    cropped_bytes = call_args[1]["Document"]["Bytes"]
    
    # Verify the cropped bytes contain a valid image
    cropped_image = Image.open(BytesIO(cropped_bytes))
    assert cropped_image.size == (200, 100)


def test_textract_ocr_handles_multiple_lines_with_spacing(textract_ocr, mock_textract_client, sample_image_bytes):
    """Test that multiple lines are joined with spaces"""
    # Arrange
    mock_response = {
        "Blocks": [
            {"BlockType": "LINE", "Text": "First", "Confidence": 99.0},
            {"BlockType": "LINE", "Text": "Second", "Confidence": 98.0},
            {"BlockType": "LINE", "Text": "Third", "Confidence": 97.0}
        ]
    }
    mock_textract_client.detect_document_text.return_value = mock_response
    
    # Act
    result = textract_ocr.extract_text(
        image_bytes=sample_image_bytes,
        x=0.0,
        y=0.0,
        width=100.0,
        height=100.0
    )
    
    # Assert
    assert result == "First Second Third"


def test_textract_ocr_handles_zero_dimensions(textract_ocr, mock_textract_client, sample_image_bytes):
    """Test that zero dimensions are handled gracefully"""
    # Arrange
    mock_response = {"Blocks": []}
    mock_textract_client.detect_document_text.return_value = mock_response
    
    # Act & Assert - should not crash with zero width/height
    result = textract_ocr.extract_text(
        image_bytes=sample_image_bytes,
        x=100.0,
        y=100.0,
        width=0.0,
        height=0.0
    )
    
    assert result == ""
