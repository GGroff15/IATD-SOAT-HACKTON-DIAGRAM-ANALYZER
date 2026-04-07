"""Integration tests for OCR text extraction workflow."""

from io import BytesIO
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.adapter.driven.ocr.paddle_ocr import PaddleOCRExtractor
from app.core.application.exceptions import TextExtractionError


@pytest.fixture
def mock_ocr_engine() -> MagicMock:
    """Provide mock PaddleOCR engine for integration testing."""
    engine = MagicMock()
    engine.predict.return_value = [{"rec_texts": ["Sample Text"]}]
    return engine


@pytest.fixture
def paddle_ocr(mock_ocr_engine: MagicMock) -> PaddleOCRExtractor:
    """Provide PaddleOCR adapter for integration testing."""
    return PaddleOCRExtractor(ocr_engine=mock_ocr_engine, use_angle_cls=True)


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


def test_paddle_ocr_initialization(paddle_ocr: PaddleOCRExtractor) -> None:
    """Test that PaddleOCR adapter initializes successfully."""
    assert paddle_ocr.ocr_engine is not None


def test_paddle_ocr_extract_text_from_region(
    paddle_ocr: PaddleOCRExtractor,
    sample_image_with_text: bytes,
) -> None:
    """Test extracting text from a specific region of an image."""
    result = paddle_ocr.extract_text(
        image_bytes=sample_image_with_text,
        x=50.0,
        y=50.0,
        width=300.0,
        height=100.0,
    )

    assert isinstance(result, str)
    assert result == "Sample Text"
    paddle_ocr.ocr_engine.predict.assert_called_once()


def test_paddle_ocr_extract_text_empty_region(paddle_ocr: PaddleOCRExtractor) -> None:
    """Test extracting text from an empty region (no text)."""
    img = Image.new("RGB", (200, 200), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    paddle_ocr.ocr_engine.predict.return_value = [{"rec_texts": []}]

    result = paddle_ocr.extract_text(
        image_bytes=image_bytes,
        x=10.0,
        y=10.0,
        width=50.0,
        height=50.0,
    )

    assert result == ""


def test_paddle_ocr_multiple_text_lines(
    paddle_ocr: PaddleOCRExtractor,
    sample_image_with_text: bytes,
) -> None:
    """Test extracting multiple lines of text."""
    paddle_ocr.ocr_engine.predict.return_value = [
        {"rec_texts": ["First Line", "Second Line", "Third Line"]}
    ]

    result = paddle_ocr.extract_text(
        image_bytes=sample_image_with_text,
        x=0.0,
        y=0.0,
        width=400.0,
        height=200.0,
    )

    assert result == "First Line Second Line Third Line"


def test_paddle_ocr_crops_image_correctly(paddle_ocr: PaddleOCRExtractor) -> None:
    """Test that image is cropped to specified bounding box before OCR."""
    img = Image.new("RGB", (800, 600), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    paddle_ocr.ocr_engine.predict.return_value = [{"rec_texts": ["Cropped"]}]

    result = paddle_ocr.extract_text(
        image_bytes=image_bytes,
        x=100.0,
        y=150.0,
        width=200.0,
        height=100.0,
    )

    assert result == "Cropped"

    call_args = paddle_ocr.ocr_engine.predict.call_args
    cropped_array = call_args[0][0]
    assert isinstance(cropped_array, np.ndarray)
    assert cropped_array.shape[:2] == (100, 200)


def test_paddle_ocr_handles_zero_dimensions(
    paddle_ocr: PaddleOCRExtractor,
    sample_image_with_text: bytes,
) -> None:
    """Test that zero dimensions are handled gracefully without OCR calls."""
    result = paddle_ocr.extract_text(
        image_bytes=sample_image_with_text,
        x=100.0,
        y=100.0,
        width=0.0,
        height=0.0,
    )

    assert result == ""
    paddle_ocr.ocr_engine.predict.assert_not_called()


def test_paddle_ocr_error_handling(
    paddle_ocr: PaddleOCRExtractor,
    sample_image_with_text: bytes,
) -> None:
    """Test that engine errors are properly handled and mapped."""
    paddle_ocr.ocr_engine.predict.side_effect = RuntimeError("invalid image")
    paddle_ocr.ocr_engine.ocr.side_effect = RuntimeError("legacy invalid image")

    with pytest.raises(TextExtractionError, match="Failed to extract text"):
        paddle_ocr.extract_text(
            image_bytes=sample_image_with_text,
            x=0.0,
            y=0.0,
            width=100.0,
            height=100.0,
        )
