"""Integration tests for remote YOLO component detection mapping."""

from uuid import uuid4
from unittest.mock import Mock

import pytest

from app.adapter.driven.detection.yolo_detector import YoloDetector
from app.adapter.driven.detection.yolo_inference_client import (
    InferenceDetection,
    YoloInferenceClientError,
)
from app.core.application.exceptions import DiagramDetectionError
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult


def test_yolo_detector_returns_components_from_remote_detections():
    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="service", x1=100.0, y1=100.0, x2=220.0, y2=180.0),
        InferenceDetection(label="database", x1=300.0, y1=100.0, x2=430.0, y2=190.0),
    )
    detector = YoloDetector(inference_client=inference_client)

    result = detector.detect(diagram_upload_id=uuid4(), image_bytes=b"png")

    assert isinstance(result, DiagramAnalysisResult)
    assert result.component_count == 2
    assert result.components[0].class_name == "service"
    assert result.components[1].class_name == "database"


def test_yolo_detector_ignores_arrow_only_detections():
    inference_client = Mock()
    inference_client.infer.return_value = (
        InferenceDetection(label="arrow_line", x1=130.0, y1=70.0, x2=300.0, y2=90.0),
        InferenceDetection(label="arrow_head", x1=290.0, y1=60.0, x2=315.0, y2=95.0),
    )
    detector = YoloDetector(inference_client=inference_client)

    result = detector.detect(diagram_upload_id=uuid4(), image_bytes=b"png")

    assert result.component_count == 0


def test_yolo_detector_surfaces_remote_failures():
    inference_client = Mock()
    inference_client.infer.side_effect = YoloInferenceClientError("service unavailable")
    detector = YoloDetector(inference_client=inference_client)

    with pytest.raises(DiagramDetectionError, match="Failed to detect components"):
        detector.detect(diagram_upload_id=uuid4(), image_bytes=b"png")
