from io import BytesIO
from unittest.mock import MagicMock, Mock

import numpy as np
import pytest
from PIL import Image

from app.core.application.exceptions import TextExtractionError


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Generate sample PNG image bytes for testing."""
    img = Image.new("RGB", (640, 480), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def mock_ocr_engine() -> MagicMock:
    """Mock PaddleOCR engine instance for testing."""
    return MagicMock()


@pytest.fixture
def paddle_text_extractor(mock_ocr_engine: MagicMock):
    """PaddleOCRExtractor instance with mocked OCR engine."""
    from app.adapter.driven.ocr.paddle_ocr import PaddleOCRExtractor

    return PaddleOCRExtractor(ocr_engine=mock_ocr_engine, use_angle_cls=True)


def test_paddle_ocr_extract_text_success_with_predict(
    paddle_text_extractor,
    mock_ocr_engine: MagicMock,
    sample_image_bytes: bytes,
) -> None:
    """Test successful text extraction using predict-style response."""
    mock_ocr_engine.predict.return_value = [{"rec_texts": ["Login", "Button"]}]

    result = paddle_text_extractor.extract_text(
        image_bytes=sample_image_bytes,
        x=100.0,
        y=200.0,
        width=150.0,
        height=50.0,
    )

    assert result == "Login Button"
    mock_ocr_engine.predict.assert_called_once()

    cropped_input = mock_ocr_engine.predict.call_args[0][0]
    assert isinstance(cropped_input, np.ndarray)
    assert cropped_input.shape[:2] == (50, 150)


def test_paddle_ocr_extract_text_success_with_legacy_ocr(sample_image_bytes: bytes) -> None:
    """Test successful extraction from legacy ocr()-style nested output."""
    legacy_engine = Mock(spec=["ocr"])
    legacy_engine.ocr.return_value = [
        [
            [[[0, 0], [1, 0], [1, 1], [0, 1]], ("Submit", 0.98)],
            [[[2, 2], [3, 2], [3, 3], [2, 3]], ("Now", 0.95)],
        ]
    ]

    from app.adapter.driven.ocr.paddle_ocr import PaddleOCRExtractor

    extractor = PaddleOCRExtractor(ocr_engine=legacy_engine, use_angle_cls=True)

    result = extractor.extract_text(
        image_bytes=sample_image_bytes,
        x=0.0,
        y=0.0,
        width=120.0,
        height=80.0,
    )

    assert result == "Submit Now"
    legacy_engine.ocr.assert_called_once()


def test_paddle_ocr_extract_text_empty_result(
    paddle_text_extractor,
    mock_ocr_engine: MagicMock,
    sample_image_bytes: bytes,
) -> None:
    """Test empty string return when OCR detects no text."""
    mock_ocr_engine.predict.return_value = [{"rec_texts": []}]

    result = paddle_text_extractor.extract_text(
        image_bytes=sample_image_bytes,
        x=10.0,
        y=20.0,
        width=100.0,
        height=30.0,
    )

    assert result == ""


def test_paddle_ocr_handles_zero_dimensions(
    paddle_text_extractor,
    mock_ocr_engine: MagicMock,
    sample_image_bytes: bytes,
) -> None:
    """Test that zero dimensions short-circuit without engine calls."""
    result = paddle_text_extractor.extract_text(
        image_bytes=sample_image_bytes,
        x=100.0,
        y=100.0,
        width=0.0,
        height=0.0,
    )

    assert result == ""
    mock_ocr_engine.predict.assert_not_called()
    mock_ocr_engine.ocr.assert_not_called()


def test_paddle_ocr_maps_engine_errors(
    paddle_text_extractor,
    mock_ocr_engine: MagicMock,
    sample_image_bytes: bytes,
) -> None:
    """Test that OCR engine errors are mapped to TextExtractionError."""
    mock_ocr_engine.predict.side_effect = RuntimeError("model error")
    mock_ocr_engine.ocr.side_effect = RuntimeError("legacy model error")

    with pytest.raises(TextExtractionError, match="Failed to extract text"):
        paddle_text_extractor.extract_text(
            image_bytes=sample_image_bytes,
            x=100.0,
            y=200.0,
            width=50.0,
            height=50.0,
        )


def test_paddle_ocr_falls_back_to_legacy_ocr_when_predict_fails(
    paddle_text_extractor,
    mock_ocr_engine: MagicMock,
    sample_image_bytes: bytes,
) -> None:
    """Test that runtime failures in predict() fall back to ocr() parsing."""
    mock_ocr_engine.predict.side_effect = RuntimeError("predict backend failure")
    mock_ocr_engine.ocr.return_value = [
        [
            [[[0, 0], [1, 0], [1, 1], [0, 1]], ("Fallback", 0.99)],
            [[[2, 2], [3, 2], [3, 3], [2, 3]], ("Text", 0.94)],
        ]
    ]

    result = paddle_text_extractor.extract_text(
        image_bytes=sample_image_bytes,
        x=0.0,
        y=0.0,
        width=160.0,
        height=80.0,
    )

    assert result == "Fallback Text"
    mock_ocr_engine.predict.assert_called_once()
    mock_ocr_engine.ocr.assert_called_once()
