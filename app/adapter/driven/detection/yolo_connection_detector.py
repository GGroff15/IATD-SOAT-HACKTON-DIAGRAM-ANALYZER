from dataclasses import dataclass
from math import hypot

import structlog

from app.adapter.driven.detection.yolo_inference_client import (
    InferenceDetection,
    YoloInferenceClient,
    YoloInferenceClientError,
)
from app.core.application.exceptions import ConnectionDetectionError
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType, DetectedConnection

logger = structlog.get_logger()


@dataclass(frozen=True)
class _Detection:
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


class YoloConnectionDetector:
    """Adapter for detecting directed connections from remote YOLO detections."""

    def __init__(
        self,
        inference_client: YoloInferenceClient,
        arrow_line_class_name: str = "arrow_line",
        arrow_head_class_name: str = "arrow_head",
    ):
        self.inference_client = inference_client
        self.arrow_line_class_name = arrow_line_class_name
        self.arrow_head_class_name = arrow_head_class_name

        logger.info(
            "yolo_connection_detector.initializing",
            arrow_line_class_name=arrow_line_class_name,
            arrow_head_class_name=arrow_head_class_name,
        )
        logger.info("yolo_connection_detector.initialized")

    def detect(
        self,
        image_bytes: bytes,
        components: tuple[DetectedComponent, ...],
    ) -> tuple[DetectedConnection, ...]:
        """Detect connections using YOLO classes arrow_line and arrow_head."""
        logger.info(
            "connection_detection.started",
            image_size_bytes=len(image_bytes),
            component_count=len(components),
        )

        try:
            detections = self._extract_detections(self.inference_client.infer(image_bytes))
            line_detections = [
                detection
                for detection in detections
                if detection.class_name == self.arrow_line_class_name
            ]
            head_detections = [
                detection
                for detection in detections
                if detection.class_name == self.arrow_head_class_name
            ]

            if not line_detections:
                logger.info("connection_detection.completed", connection_count=0)
                return tuple()

            connections: list[DetectedConnection] = []
            for line_detection in line_detections:
                nearest_component_indices = self._find_two_nearest_components(
                    line_detection.center,
                    components,
                )

                if head_detections:
                    matched_head = self._find_nearest_detection(
                        line_detection.center,
                        head_detections,
                    )
                    target_idx = self._find_nearest_component_index(
                        matched_head.center,
                        components,
                    )
                    source_idx = self._resolve_source_component_index(
                        target_idx,
                        nearest_component_indices,
                        line_detection.center,
                        components,
                    )
                    connection_type = (
                        ConnectionType.ARROW if target_idx is not None else ConnectionType.STRAIGHT
                    )
                else:
                    source_idx, target_idx = self._resolve_undirected_component_pair(
                        nearest_component_indices,
                    )
                    connection_type = ConnectionType.STRAIGHT

                start_point = self._resolve_connection_point(
                    source_idx,
                    components,
                    fallback=line_detection.center,
                )
                end_point = self._resolve_connection_point(
                    target_idx,
                    components,
                    fallback=line_detection.center,
                )

                if source_idx is not None and target_idx is not None and source_idx == target_idx:
                    second_idx = self._find_nearest_component_index(
                        line_detection.center,
                        components,
                        exclude_index=target_idx,
                    )
                    if second_idx is not None:
                        source_idx = second_idx
                        start_point = self._resolve_connection_point(
                            source_idx,
                            components,
                            fallback=line_detection.center,
                        )

                connection = DetectedConnection(
                    connection_type=connection_type,
                    confidence=line_detection.confidence,
                    start_point=start_point,
                    end_point=end_point,
                    source_component_index=source_idx,
                    target_component_index=target_idx,
                )
                connections.append(connection)

            logger.info(
                "connection_detection.completed",
                line_detection_count=len(line_detections),
                head_detection_count=len(head_detections),
                connection_count=len(connections),
            )
            return tuple(connections)
        except YoloInferenceClientError as exc:
            raise ConnectionDetectionError(f"Failed to detect connections: {exc}") from exc
        except Exception as exc:
            logger.error(
                "connection_detection.failed",
                error=str(exc),
                exc_info=True,
            )
            raise ConnectionDetectionError(f"Failed to detect connections: {exc}") from exc

    @staticmethod
    def _extract_detections(raw_detections: tuple[InferenceDetection, ...]) -> list[_Detection]:
        return [
            _Detection(
                class_name=detection.label,
                confidence=detection.confidence,
                x1=detection.x1,
                y1=detection.y1,
                x2=detection.x2,
                y2=detection.y2,
            )
            for detection in raw_detections
        ]

    def _find_nearest_detection(
        self,
        point: tuple[float, float],
        detections: list[_Detection],
    ) -> _Detection:
        return min(detections, key=lambda detection: self._distance(point, detection.center))

    def _find_two_nearest_components(
        self,
        point: tuple[float, float],
        components: tuple[DetectedComponent, ...],
    ) -> list[int]:
        sorted_indices = sorted(
            range(len(components)),
            key=lambda index: (self._distance(point, self._component_center(components[index])), index),
        )
        return sorted_indices[:2]

    def _resolve_undirected_component_pair(
        self,
        nearest_component_indices: list[int],
    ) -> tuple[int | None, int | None]:
        if not nearest_component_indices:
            return None, None
        if len(nearest_component_indices) == 1:
            return nearest_component_indices[0], None
        return nearest_component_indices[0], nearest_component_indices[1]

    def _resolve_source_component_index(
        self,
        target_idx: int | None,
        nearest_component_indices: list[int],
        line_center: tuple[float, float],
        components: tuple[DetectedComponent, ...],
    ) -> int | None:
        if target_idx is None:
            if not nearest_component_indices:
                return None
            return nearest_component_indices[0]

        for index in nearest_component_indices:
            if index != target_idx:
                return index

        return self._find_nearest_component_index(
            line_center,
            components,
            exclude_index=target_idx,
        )

    def _find_nearest_component_index(
        self,
        point: tuple[float, float],
        components: tuple[DetectedComponent, ...],
        exclude_index: int | None = None,
    ) -> int | None:
        best_index: int | None = None
        best_distance: float | None = None

        for index, component in enumerate(components):
            if exclude_index is not None and index == exclude_index:
                continue
            distance = self._distance(point, self._component_center(component))
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = index

        return best_index

    def _resolve_connection_point(
        self,
        component_index: int | None,
        components: tuple[DetectedComponent, ...],
        fallback: tuple[float, float],
    ) -> tuple[float, float]:
        if component_index is None:
            return fallback

        component = components[component_index]
        return self._component_center(component)

    @staticmethod
    def _component_center(component: DetectedComponent) -> tuple[float, float]:
        return (component.x + component.width / 2.0, component.y + component.height / 2.0)

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return hypot(a[0] - b[0], a[1] - b[1])
