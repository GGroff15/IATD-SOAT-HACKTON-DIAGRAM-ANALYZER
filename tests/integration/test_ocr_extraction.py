"""Integration tests for OCR text extraction workflow."""
from io import BytesIO
from unittest.mock import MagicMock
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.adapter.driven.ocr.textract_ocr import TextractOCR
from app.core.application.exceptions import TextExtractionError


@pytest.fixture
def mock_textract_client():
    """Provide mock Textract client for integration testing.
    
    In a real integration test with LocalStack, this would be replaced
    with a real boto3 textract client pointing to LocalStack endpoint.
    """
    client = MagicMock()
    client.detect_document_text.return_value = {
        "Blocks": [
            {"BlockType": "LINE", "Text": "Sample Text", "Confidence": 99.5}
        ]
    }
    return client


@pytest.fixture
def textract_ocr(mock_textract_client):
    """Provide TextractOCR adapter for integration testing."""
    return TextractOCR(textract_client=mock_textract_client)


@pytest.fixture
def sample_image_with_text():
    """Create an image with text for OCR testing."""
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)
    
    # Draw a simple text box
    draw.rectangle([50, 50, 350, 150], fill="lightblue", outline="black", width=2)
    
    # Note: For actual text, you'd need a font file. For testing, we just draw shapes.
    # Real Textract would process the actual text in the image.
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_textract_ocr_initialization(textract_ocr):
    """Test that TextractOCR initializes successfully."""
    assert textract_ocr.textract_client is not None


def test_textract_ocr_extract_text_from_region(textract_ocr, sample_image_with_text):
    """Test extracting text from a specific region of an image."""
    # Act
    result = textract_ocr.extract_text(
        image_bytes=sample_image_with_text,
        x=50.0,
        y=50.0,
        width=300.0,
        height=100.0
    )
    
    # Assert
    assert isinstance(result, str)
    assert result == "Sample Text"
    textract_ocr.textract_client.detect_document_text.assert_called_once()


def test_textract_ocr_extract_text_empty_region(textract_ocr):
    """Test extracting text from an empty region (no text)."""
    # Arrange
    img = Image.new("RGB", (200, 200), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    
    textract_ocr.textract_client.detect_document_text.return_value = {"Blocks": []}
    
    # Act
    result = textract_ocr.extract_text(
        image_bytes=image_bytes,
        x=10.0,
        y=10.0,
        width=50.0,
        height=50.0
    )
    
    # Assert
    assert result == ""


def test_textract_ocr_multiple_text_lines(textract_ocr, sample_image_with_text):
    """Test extracting multiple lines of text."""
    # Arrange
    textract_ocr.textract_client.detect_document_text.return_value = {
        "Blocks": [
            {"BlockType": "LINE", "Text": "First Line", "Confidence": 99.0},
            {"BlockType": "LINE", "Text": "Second Line", "Confidence": 98.5},
            {"BlockType": "LINE", "Text": "Third Line", "Confidence": 97.0}
        ]
    }
    
    # Act
    result = textract_ocr.extract_text(
        image_bytes=sample_image_with_text,
        x=0.0,
        y=0.0,
        width=400.0,
        height=200.0
    )
    
    # Assert
    assert result == "First Line Second Line Third Line"


def test_textract_ocr_crops_image_correctly(textract_ocr):
    """Test that image is cropped to specified bounding box before OCR."""
    # Arrange
    img = Image.new("RGB", (800, 600), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    
    textract_ocr.textract_client.detect_document_text.return_value = {
        "Blocks": [{"BlockType": "LINE", "Text": "Cropped"}]
    }
    
    # Act
    result = textract_ocr.extract_text(
        image_bytes=image_bytes,
        x=100.0,
        y=150.0,
        width=200.0,
        height=100.0
    )
    
    # Assert
    assert result == "Cropped"
    
    # Verify that detect_document_text was called
    call_args = textract_ocr.textract_client.detect_document_text.call_args
    cropped_bytes = call_args[1]["Document"]["Bytes"]
    
    # Verify the cropped image has correct dimensions
    cropped_img = Image.open(BytesIO(cropped_bytes))
    assert cropped_img.size == (200, 100)


def test_textract_ocr_handles_zero_dimensions(textract_ocr, sample_image_with_text):
    """Test that zero dimensions are handled gracefully without calling Textract."""
    # Act
    result = textract_ocr.extract_text(
        image_bytes=sample_image_with_text,
        x=100.0,
        y=100.0,
        width=0.0,
        height=0.0
    )
    
    # Assert
    assert result == ""
    # Textract should not be called for zero dimensions
    textract_ocr.textract_client.detect_document_text.assert_not_called()


def test_textract_ocr_error_handling(textract_ocr, sample_image_with_text):
    """Test that Textract errors are properly handled and mapped."""
    # Arrange
    from botocore.exceptions import ClientError
    
    error_response = {"Error": {"Code": "InvalidImageException", "Message": "Invalid image"}}
    textract_ocr.textract_client.detect_document_text.side_effect = ClientError(
        error_response, "DetectDocumentText"
    )
    
    # Act & Assert
    with pytest.raises(TextExtractionError, match="Failed to extract text"):
        textract_ocr.extract_text(
            image_bytes=sample_image_with_text,
            x=0.0,
            y=0.0,
            width=100.0,
            height=100.0
        )


@pytest.mark.integration
@pytest.mark.skipif(
    True,  # Set to False when LocalStack Textract is available
    reason="Requires LocalStack with Textract support"
)
def test_textract_ocr_with_localstack():
    """Integration test with real LocalStack Textract service.
    
    This test is skipped by default and requires LocalStack running
    with Textract service enabled.
    """
    import boto3
    
    # Create real Textract client pointing to LocalStack
    textract_client = boto3.client(
        "textract",
        region_name="us-east-1",
        endpoint_url="http://localhost:4566",
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    
    ocr = TextractOCR(textract_client=textract_client)
    
    # Create simple test image
    img = Image.new("RGB", (400, 200), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    
    # Act
    result = ocr.extract_text(
        image_bytes=image_bytes,
        x=0.0,
        y=0.0,
        width=400.0,
        height=200.0
    )
    
    # Assert
    assert isinstance(result, str)
