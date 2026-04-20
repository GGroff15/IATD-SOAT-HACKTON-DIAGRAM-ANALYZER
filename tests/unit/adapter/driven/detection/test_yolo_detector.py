from uuid import uuid4
from unittest.mock import Mock

import pytest

from app.adapter.driven.detection.yolo_inference_client import (
    InferenceDetection,
    YoloInferenceClientError,
)
from app.adapter.driven.detection.yolo_detector import YoloDetector
from app.core.application.exceptions import DiagramDetectionError
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult


def test_yolo_detector_maps_remote_detections_to_components():
    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="service", x1=10.0, y1=20.0, x2=60.0, y2=80.0),
        InferenceDetection(label="database", x1=100.0, y1=150.0, x2=220.0, y2=260.0),
    )
    detector = YoloDetector(inference_client=inference_client)

    result = detector.detect(diagram_upload_id=uuid4(), image_bytes=b"fake-image-bytes")

    assert isinstance(result, DiagramAnalysisResult)
    assert result.component_count == 2
    assert result.components[0].class_name == "service"
    assert result.components[0].x == 10.0
    assert result.components[0].y == 20.0
    assert result.components[0].width == 50.0
    assert result.components[0].height == 60.0
    assert result.components[0].confidence == 1.0


def test_yolo_detector_excludes_arrow_classes_from_component_output():
    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="service", x1=10.0, y1=20.0, x2=60.0, y2=80.0),
        InferenceDetection(label="arrow_line", x1=80.0, y1=20.0, x2=140.0, y2=40.0),
        InferenceDetection(label="arrow_head", x1=140.0, y1=20.0, x2=155.0, y2=40.0),
    )
    detector = YoloDetector(
        inference_client=inference_client,
        excluded_class_names=("arrow_line", "arrow_head"),
    )

    result = detector.detect(diagram_upload_id=uuid4(), image_bytes=b"fake-image-bytes")

    assert result.component_count == 1
    assert result.components[0].class_name == "service"


def test_yolo_detector_wraps_client_errors_as_diagram_detection_error():
    inference_client = Mock()
    inference_client.infer.side_effect = YoloInferenceClientError("request failed")
    detector = YoloDetector(inference_client=inference_client)

    with pytest.raises(DiagramDetectionError, match="Failed to detect components"):
        detector.detect(diagram_upload_id=uuid4(), image_bytes=b"fake-image-bytes")
