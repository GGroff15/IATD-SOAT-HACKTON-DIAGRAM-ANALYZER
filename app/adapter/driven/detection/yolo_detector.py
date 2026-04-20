from uuid import UUID

import structlog

from app.core.application.exceptions import DiagramDetectionError
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult
from app.adapter.driven.detection.yolo_inference_client import (
    YoloInferenceClient,
    YoloInferenceClientError,
)

logger = structlog.get_logger()


class YoloDetector:
    """Adapter for detecting diagram components via external YOLO inference API."""

    def __init__(
        self,
        inference_client: YoloInferenceClient,
        excluded_class_names: tuple[str, ...] = ("arrow_line", "arrow_head"),
    ):
        self.inference_client = inference_client
        self.excluded_class_names = set(excluded_class_names)

        logger.info(
            "yolo_detector.initializing",
            excluded_class_names=sorted(self.excluded_class_names),
        )
        logger.info("yolo_detector.initialized")

    def detect(self, diagram_upload_id: UUID, image_bytes: bytes) -> DiagramAnalysisResult:
        logger.info(
            "diagram_detection.started",
            diagram_upload_id=str(diagram_upload_id),
            image_size_bytes=len(image_bytes),
        )

        try:
            detections = self.inference_client.infer(image_bytes)
            components: list[DetectedComponent] = []
            excluded_count = 0
            for detection in detections:
                if detection.label in self.excluded_class_names:
                    excluded_count += 1
                    continue
                component = DetectedComponent(
                    class_name=detection.label,
                    confidence=detection.confidence,
                    x=float(detection.x1),
                    y=float(detection.y1),
                    width=float(detection.x2 - detection.x1),
                    height=float(detection.y2 - detection.y1),
                )
                components.append(component)

            result = DiagramAnalysisResult(
                diagram_upload_id=diagram_upload_id,
                components=tuple(components),
            )

            logger.info(
                "diagram_detection.completed",
                diagram_upload_id=str(diagram_upload_id),
                component_count=len(components),
                excluded_detection_count=excluded_count,
                components=[
                    {
                        "class_name": c.class_name,
                        "confidence": round(c.confidence, 3),
                        "bbox": {
                            "x": round(c.x, 1),
                            "y": round(c.y, 1),
                            "width": round(c.width, 1),
                            "height": round(c.height, 1),
                        },
                    }
                    for c in components
                ],
            )

            return result
        except YoloInferenceClientError as exc:
            raise DiagramDetectionError(f"Failed to detect components in diagram: {exc}") from exc
        except Exception as exc:
            logger.error(
                "diagram_detection.failed",
                diagram_upload_id=str(diagram_upload_id),
                error=str(exc),
                exc_info=True,
            )
            raise DiagramDetectionError(
                f"Failed to detect components in diagram: {exc}"
            ) from exc
