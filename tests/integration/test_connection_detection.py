"""Integration tests for remote YOLO-based connection detection semantics."""

from unittest.mock import Mock

import pytest

from app.adapter.driven.detection.yolo_connection_detector import YoloConnectionDetector
from app.adapter.driven.detection.yolo_inference_client import (
    InferenceDetection,
    YoloInferenceClientError,
)
from app.core.application.exceptions import ConnectionDetectionError
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType


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
    components = create_components()

    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="arrow_line", x1=190.0, y1=214.0, x2=432.0, y2=236.0),
        InferenceDetection(label="arrow_head", x1=428.0, y1=198.0, x2=455.0, y2=242.0),
    )
    detector = YoloConnectionDetector(inference_client=inference_client)
    connections = detector.detect(image_bytes=b"png", components=components)

    assert len(connections) == 1
    connection = connections[0]
    assert connection.connection_type == ConnectionType.ARROW
    assert connection.source_component_index == 0
    assert connection.target_component_index == 1


def test_yolo_connection_detector_uses_straight_when_head_is_missing():
    components = create_components()

    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="arrow_line", x1=190.0, y1=214.0, x2=432.0, y2=236.0),
    )
    detector = YoloConnectionDetector(inference_client=inference_client)
    connections = detector.detect(image_bytes=b"png", components=components)

    assert len(connections) == 1
    assert connections[0].connection_type == ConnectionType.STRAIGHT


def test_yolo_connection_detector_returns_empty_when_no_arrow_line_detected():
    components = create_components()

    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="arrow_head", x1=428.0, y1=198.0, x2=455.0, y2=242.0),
    )
    detector = YoloConnectionDetector(inference_client=inference_client)
    connections = detector.detect(image_bytes=b"png", components=components)

    assert connections == tuple()


def test_yolo_connection_detector_surfaces_remote_failure():
    components = create_components()

    inference_client = Mock()
    inference_client.infer.side_effect = YoloInferenceClientError("service unavailable")
    detector = YoloConnectionDetector(inference_client=inference_client)

    with pytest.raises(ConnectionDetectionError, match="Failed to detect connections"):
        detector.detect(image_bytes=b"png", components=components)
