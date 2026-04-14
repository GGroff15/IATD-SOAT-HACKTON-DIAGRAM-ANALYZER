from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from app.core.application.exceptions import ConnectionDetectionError
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType


def _mock_tensor(value):
    """Return a tensor-like mock supporting .cpu().numpy() for adapter tests."""
    tensor = MagicMock()
    tensor.cpu.return_value.numpy.return_value = value
    return tensor


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Generate sample PNG image bytes for testing."""
    image = Image.new("RGB", (640, 480), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_components() -> tuple[DetectedComponent, ...]:
    """Create deterministic components used to link connections."""
    return (
        DetectedComponent(
            class_name="service",
            confidence=0.92,
            x=80.0,
            y=180.0,
            width=120.0,
            height=80.0,
        ),
        DetectedComponent(
            class_name="database",
            confidence=0.9,
            x=420.0,
            y=180.0,
            width=120.0,
            height=80.0,
        ),
    )


@pytest.fixture
def mock_yolo_model() -> MagicMock:
    """Create a mock YOLO model for testing."""
    model = MagicMock()
    model.to = MagicMock(return_value=model)
    return model


def _mock_result(
    boxes_xyxy: list[np.ndarray],
    boxes_conf: list[float],
    boxes_cls: list[int],
    names: dict[int, str],
) -> MagicMock:
    boxes = MagicMock()
    boxes.xyxy = [_mock_tensor(value) for value in boxes_xyxy]
    boxes.conf = [_mock_tensor(np.array(value)) for value in boxes_conf]
    boxes.cls = [_mock_tensor(np.array(value)) for value in boxes_cls]
    type(boxes).__len__ = lambda _: len(boxes_xyxy)

    result = MagicMock()
    result.boxes = boxes
    result.names = names
    return result


def test_yolo_connection_detector_initialization_success(mock_yolo_model: MagicMock):
    """Test adapter initialization with valid model config."""
    from app.adapter.driven.detection.yolo_connection_detector import YoloConnectionDetector

    with patch(
        "app.adapter.driven.detection.yolo_connection_detector.YOLO",
        return_value=mock_yolo_model,
    ):
        detector = YoloConnectionDetector(
            model_name="best.pt",
            confidence_threshold=0.4,
            device="cpu",
            arrow_line_class_name="arrow_line",
            arrow_head_class_name="arrow_head",
        )

    assert detector.model_name == "best.pt"
    assert detector.confidence_threshold == 0.4
    assert detector.arrow_line_class_name == "arrow_line"
    assert detector.arrow_head_class_name == "arrow_head"
    mock_yolo_model.to.assert_called_once_with("cpu")


def test_yolo_connection_detector_returns_empty_without_arrow_lines(
    mock_yolo_model: MagicMock,
    sample_image_bytes: bytes,
    sample_components: tuple[DetectedComponent, ...],
):
    """Test detector returns no connections when no arrow_line detections exist."""
    from app.adapter.driven.detection.yolo_connection_detector import YoloConnectionDetector

    mock_yolo_model.return_value = [
        _mock_result(
            boxes_xyxy=[np.array([90.0, 190.0, 190.0, 250.0])],
            boxes_conf=[0.88],
            boxes_cls=[0],
            names={0: "component"},
        )
    ]

    with patch(
        "app.adapter.driven.detection.yolo_connection_detector.YOLO",
        return_value=mock_yolo_model,
    ):
        detector = YoloConnectionDetector(model_name="best.pt")
        connections = detector.detect(sample_image_bytes, sample_components)

    assert connections == tuple()


def test_yolo_connection_detector_builds_directed_arrow_connection(
    mock_yolo_model: MagicMock,
    sample_image_bytes: bytes,
    sample_components: tuple[DetectedComponent, ...],
):
    """Test arrow direction mapping using arrow_head as target evidence."""
    from app.adapter.driven.detection.yolo_connection_detector import YoloConnectionDetector

    # arrow_line roughly between components, arrow_head near component index 1
    mock_yolo_model.return_value = [
        _mock_result(
            boxes_xyxy=[
                np.array([180.0, 210.0, 440.0, 230.0]),  # arrow_line
                np.array([430.0, 200.0, 455.0, 235.0]),  # arrow_head near right component
            ],
            boxes_conf=[0.91, 0.85],
            boxes_cls=[0, 1],
            names={0: "arrow_line", 1: "arrow_head"},
        )
    ]

    with patch(
        "app.adapter.driven.detection.yolo_connection_detector.YOLO",
        return_value=mock_yolo_model,
    ):
        detector = YoloConnectionDetector(model_name="best.pt")
        connections = detector.detect(sample_image_bytes, sample_components)

    assert len(connections) == 1
    connection = connections[0]

    assert connection.connection_type == ConnectionType.ARROW
    assert connection.source_component_index == 0
    assert connection.target_component_index == 1

    source = sample_components[0]
    target = sample_components[1]
    expected_start = (source.x + source.width / 2.0, source.y + source.height / 2.0)
    expected_end = (target.x + target.width / 2.0, target.y + target.height / 2.0)

    assert connection.start_point == expected_start
    assert connection.end_point == expected_end
    assert 0.0 <= connection.confidence <= 1.0


def test_yolo_connection_detector_falls_back_to_straight_without_head(
    mock_yolo_model: MagicMock,
    sample_image_bytes: bytes,
    sample_components: tuple[DetectedComponent, ...],
):
    """Test detector emits straight connection when no arrow_head is available."""
    from app.adapter.driven.detection.yolo_connection_detector import YoloConnectionDetector

    mock_yolo_model.return_value = [
        _mock_result(
            boxes_xyxy=[np.array([180.0, 210.0, 440.0, 230.0])],
            boxes_conf=[0.75],
            boxes_cls=[0],
            names={0: "arrow_line"},
        )
    ]

    with patch(
        "app.adapter.driven.detection.yolo_connection_detector.YOLO",
        return_value=mock_yolo_model,
    ):
        detector = YoloConnectionDetector(model_name="best.pt")
        connections = detector.detect(sample_image_bytes, sample_components)

    assert len(connections) == 1
    connection = connections[0]

    assert connection.connection_type == ConnectionType.STRAIGHT
    assert {connection.source_component_index, connection.target_component_index} == {0, 1}


def test_yolo_connection_detector_raises_connection_error_for_invalid_image(
    mock_yolo_model: MagicMock,
):
    """Test invalid image bytes are surfaced as ConnectionDetectionError."""
    from app.adapter.driven.detection.yolo_connection_detector import YoloConnectionDetector

    with patch(
        "app.adapter.driven.detection.yolo_connection_detector.YOLO",
        return_value=mock_yolo_model,
    ):
        detector = YoloConnectionDetector(model_name="best.pt")

    with pytest.raises(ConnectionDetectionError, match="Failed to detect connections"):
        detector.detect(b"invalid-image", tuple())
