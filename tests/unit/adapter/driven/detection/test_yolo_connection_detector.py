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


@pytest.fixture
def sample_components() -> tuple[DetectedComponent, ...]:
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


def test_yolo_connection_detector_builds_directed_arrow_connection(
    sample_components: tuple[DetectedComponent, ...],
):
    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="arrow_line", x1=180.0, y1=210.0, x2=440.0, y2=230.0),
        InferenceDetection(label="arrow_head", x1=430.0, y1=200.0, x2=455.0, y2=235.0),
    )
    detector = YoloConnectionDetector(inference_client=inference_client)

    connections = detector.detect(image_bytes=b"fake-image-bytes", components=sample_components)

    assert len(connections) == 1
    connection = connections[0]
    assert connection.connection_type == ConnectionType.ARROW
    assert connection.source_component_index == 0
    assert connection.target_component_index == 1


def test_yolo_connection_detector_falls_back_to_straight_without_head(
    sample_components: tuple[DetectedComponent, ...],
):
    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="arrow_line", x1=180.0, y1=210.0, x2=440.0, y2=230.0),
    )
    detector = YoloConnectionDetector(inference_client=inference_client)

    connections = detector.detect(image_bytes=b"fake-image-bytes", components=sample_components)

    assert len(connections) == 1
    connection = connections[0]
    assert connection.connection_type == ConnectionType.STRAIGHT
    assert {connection.source_component_index, connection.target_component_index} == {0, 1}


def test_yolo_connection_detector_returns_empty_without_arrow_lines(
    sample_components: tuple[DetectedComponent, ...],
):
    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="service", x1=90.0, y1=190.0, x2=190.0, y2=250.0),
    )
    detector = YoloConnectionDetector(inference_client=inference_client)

    connections = detector.detect(image_bytes=b"fake-image-bytes", components=sample_components)

    assert connections == tuple()


def test_yolo_connection_detector_wraps_client_errors(
    sample_components: tuple[DetectedComponent, ...],
):
    inference_client = Mock()
    inference_client.infer.side_effect = YoloInferenceClientError("request failed")
    detector = YoloConnectionDetector(inference_client=inference_client)

    with pytest.raises(ConnectionDetectionError, match="Failed to detect connections"):
        detector.detect(image_bytes=b"fake-image-bytes", components=sample_components)
