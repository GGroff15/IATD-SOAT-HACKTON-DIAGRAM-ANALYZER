"""Integration tests for YOLO-based connection detection semantics."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from app.adapter.driven.detection.yolo_connection_detector import YoloConnectionDetector
from app.core.application.exceptions import ConnectionDetectionError
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType


def _mock_tensor(value):
    tensor = MagicMock()
    tensor.cpu.return_value.numpy.return_value = value
    return tensor


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


def create_blank_image(width: int = 640, height: int = 480) -> bytes:
    image = Image.new("RGB", (width, height), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def create_components() -> tuple[DetectedComponent, ...]:
    return (
        DetectedComponent(
            class_name="service",
            confidence=0.95,
            x=60.0,
            y=180.0,
            width=130.0,
            height=90.0,
        ),
        DetectedComponent(
            class_name="database",
            confidence=0.93,
            x=430.0,
            y=180.0,
            width=130.0,
            height=90.0,
        ),
    )


def test_yolo_connection_detector_identifies_arrow_direction_from_head_label():
    """arrow_head near a component defines the target direction for arrow_line."""
    components = create_components()
    image_bytes = create_blank_image()

    mock_model = MagicMock()
    mock_model.to = MagicMock(return_value=mock_model)
    mock_model.return_value = [
        _mock_result(
            boxes_xyxy=[
                np.array([190.0, 214.0, 432.0, 236.0]),
                np.array([428.0, 198.0, 455.0, 242.0]),
            ],
            boxes_conf=[0.9, 0.87],
            boxes_cls=[0, 1],
            names={0: "arrow_line", 1: "arrow_head"},
        )
    ]

    with patch(
        "app.adapter.driven.detection.yolo_connection_detector.YOLO",
        return_value=mock_model,
    ):
        detector = YoloConnectionDetector(model_name="best.pt")
        connections = detector.detect(image_bytes=image_bytes, components=components)

    assert len(connections) == 1
    connection = connections[0]
    assert connection.connection_type == ConnectionType.ARROW
    assert connection.source_component_index == 0
    assert connection.target_component_index == 1


def test_yolo_connection_detector_uses_straight_when_head_is_missing():
    """arrow_line without arrow_head remains a straight connection."""
    components = create_components()
    image_bytes = create_blank_image()

    mock_model = MagicMock()
    mock_model.to = MagicMock(return_value=mock_model)
    mock_model.return_value = [
        _mock_result(
            boxes_xyxy=[np.array([190.0, 214.0, 432.0, 236.0])],
            boxes_conf=[0.82],
            boxes_cls=[0],
            names={0: "arrow_line"},
        )
    ]

    with patch(
        "app.adapter.driven.detection.yolo_connection_detector.YOLO",
        return_value=mock_model,
    ):
        detector = YoloConnectionDetector(model_name="best.pt")
        connections = detector.detect(image_bytes=image_bytes, components=components)

    assert len(connections) == 1
    connection = connections[0]
    assert connection.connection_type == ConnectionType.STRAIGHT
    assert {connection.source_component_index, connection.target_component_index} == {0, 1}


def test_yolo_connection_detector_returns_empty_when_no_arrow_line_detected():
    """No arrow_line class should produce no detected connections."""
    components = create_components()
    image_bytes = create_blank_image()

    mock_model = MagicMock()
    mock_model.to = MagicMock(return_value=mock_model)
    mock_model.return_value = [
        _mock_result(
            boxes_xyxy=[np.array([428.0, 198.0, 455.0, 242.0])],
            boxes_conf=[0.87],
            boxes_cls=[1],
            names={1: "arrow_head"},
        )
    ]

    with patch(
        "app.adapter.driven.detection.yolo_connection_detector.YOLO",
        return_value=mock_model,
    ):
        detector = YoloConnectionDetector(model_name="best.pt")
        connections = detector.detect(image_bytes=image_bytes, components=components)

    assert connections == tuple()


def test_yolo_connection_detector_raises_error_for_corrupted_image_bytes():
    """Corrupted image bytes must raise ConnectionDetectionError."""
    mock_model = MagicMock()
    mock_model.to = MagicMock(return_value=mock_model)

    with patch(
        "app.adapter.driven.detection.yolo_connection_detector.YOLO",
        return_value=mock_model,
    ):
        detector = YoloConnectionDetector(model_name="best.pt")

    with pytest.raises(ConnectionDetectionError, match="Failed to detect connections"):
        detector.detect(image_bytes=b"not-a-valid-image", components=tuple())
