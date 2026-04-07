import math
from typing import Iterable

import cv2
import numpy as np
import structlog

from app.core.application.exceptions import ConnectionDetectionError
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import (
    ConnectionType,
    DetectedConnection,
)

logger = structlog.get_logger()


class OpenCVConnectionDetector:
    """Adapter for detecting connections (lines, arrows) in diagrams using OpenCV."""

    def __init__(
        self,
        line_threshold: int = 80,
        min_line_length: int = 30,
        max_line_gap: int = 10,
        canny_low: int = 50,
        canny_high: int = 150,
        proximity_threshold: float = 30.0,
        border_margin: float = 4.0,
        max_component_overlap_ratio: float = 0.35,
        anchor_distance_threshold: float | None = None,
        dedup_endpoint_tolerance: float = 10.0,
        dedup_angle_tolerance: float = 6.0,
        morphology_kernel_size: int = 1,
        min_confidence: float = 0.35,
        arrow_window_size: int = 14,
        max_connections_per_component_pair: int = 1,
    ):
        """Initialize the OpenCV connection detector.

        Args:
            line_threshold: Accumulator threshold for Hough Line Transform
            min_line_length: Minimum line length in pixels
            max_line_gap: Maximum gap between line segments to treat as single line
            canny_low: Lower threshold for Canny edge detection
            canny_high: Upper threshold for Canny edge detection
            proximity_threshold: Maximum distance (pixels) to link connection to component
            border_margin: Max distance from bbox border to treat a line as border artifact
            max_component_overlap_ratio: Max line overlap ratio allowed with any component bbox
            anchor_distance_threshold: Distance for endpoint anchoring validation
            dedup_endpoint_tolerance: Endpoint distance tolerance to merge duplicate lines
            dedup_angle_tolerance: Angle tolerance (degrees) to merge duplicate lines
            morphology_kernel_size: Morphological cleanup kernel size for edge image
            min_confidence: Minimum confidence required to keep a detected connection
            arrow_window_size: Pixel window radius used for arrowhead endpoint analysis
            max_connections_per_component_pair: Maximum accepted connections per source/target pair
        """
        self.line_threshold = line_threshold
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.proximity_threshold = proximity_threshold
        self.border_margin = border_margin
        self.max_component_overlap_ratio = max_component_overlap_ratio
        self.anchor_distance_threshold = (
            proximity_threshold
            if anchor_distance_threshold is None
            else anchor_distance_threshold
        )
        self.dedup_endpoint_tolerance = dedup_endpoint_tolerance
        self.dedup_angle_tolerance = dedup_angle_tolerance
        self.morphology_kernel_size = max(1, morphology_kernel_size)
        self.min_confidence = min_confidence
        self.arrow_window_size = max(6, arrow_window_size)
        self.max_connections_per_component_pair = max(1, max_connections_per_component_pair)

        logger.info(
            "opencv_connection_detector.initializing",
            line_threshold=line_threshold,
            min_line_length=min_line_length,
            max_line_gap=max_line_gap,
            canny_low=canny_low,
            canny_high=canny_high,
            proximity_threshold=proximity_threshold,
            border_margin=border_margin,
            max_component_overlap_ratio=max_component_overlap_ratio,
            anchor_distance_threshold=self.anchor_distance_threshold,
            dedup_endpoint_tolerance=dedup_endpoint_tolerance,
            dedup_angle_tolerance=dedup_angle_tolerance,
            morphology_kernel_size=self.morphology_kernel_size,
            min_confidence=min_confidence,
            arrow_window_size=self.arrow_window_size,
            max_connections_per_component_pair=self.max_connections_per_component_pair,
        )

    def detect(
        self,
        image_bytes: bytes,
        components: tuple[DetectedComponent, ...],
    ) -> tuple[DetectedConnection, ...]:
        """Detect connections (lines, arrows) between components in a diagram image.

        Args:
            image_bytes: PNG image content as bytes
            components: Tuple of detected components to use as context for linking connections

        Returns:
            Tuple of DetectedConnection objects representing lines, arrows, and other
            connections found in the diagram

        Raises:
            ConnectionDetectionError: If the connection detection operation fails
        """
        logger.info(
            "connection_detection.started",
            image_size_bytes=len(image_bytes),
            component_count=len(components),
        )

        try:
            # Decode image from bytes
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                raise ConnectionDetectionError("Failed to decode image bytes")

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            edges = self._build_edges(gray)

            # Detect lines using Hough Line Transform
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=self.line_threshold,
                minLineLength=self.min_line_length,
                maxLineGap=self.max_line_gap,
            )

            if lines is None or len(lines) == 0:
                logger.info("connection_detection.completed", connection_count=0)
                return tuple()

            raw_lines = [tuple(float(value) for value in line[0]) for line in lines]
            candidate_lines = self._deduplicate_lines(raw_lines)

            # Process detected lines into connections
            connections: list[DetectedConnection] = []
            rejected_by_component_overlap = 0
            rejected_by_anchor = 0
            rejected_by_confidence = 0

            for x1, y1, x2, y2 in candidate_lines:
                start_point = (x1, y1)
                end_point = (x2, y2)

                # Filter out lines that are mostly inside component bounding boxes
                if self._is_line_inside_component(start_point, end_point, components):
                    rejected_by_component_overlap += 1
                    continue

                # Link to nearby components
                source_idx = self._find_nearest_component(start_point, components)
                target_idx = self._find_nearest_component(end_point, components)

                arrow_evidence = (
                    self._has_arrowhead(start_point, end_point, edges)
                    or self._has_arrowhead(end_point, start_point, edges)
                )

                if (
                    len(components) >= 2
                    and (
                        source_idx is None
                        or target_idx is None
                        or source_idx == target_idx
                    )
                    and not arrow_evidence
                ):
                    rejected_by_anchor += 1
                    continue

                if (
                    len(components) >= 2
                    and source_idx is None
                    and target_idx is None
                    and not arrow_evidence
                    and not self._is_line_anchored(start_point, end_point, components)
                ):
                    rejected_by_anchor += 1
                    continue

                connection_type = self._classify_connection_type(
                    start_point,
                    end_point,
                    edges,
                    arrow_evidence,
                )
                confidence = self._calculate_confidence(
                    start_point,
                    end_point,
                    edges,
                    components,
                    source_idx,
                    target_idx,
                    arrow_evidence,
                )

                if confidence < self.min_confidence:
                    rejected_by_confidence += 1
                    continue

                connection = DetectedConnection(
                    connection_type=connection_type,
                    confidence=confidence,
                    start_point=start_point,
                    end_point=end_point,
                    source_component_index=source_idx,
                    target_component_index=target_idx,
                )
                connections.append(connection)

            if components:
                connections = self._deduplicate_component_pairs(connections)

            connections_tuple = tuple(connections)
            logger.info(
                "connection_detection.completed",
                candidate_line_count=len(candidate_lines),
                rejected_by_component_overlap=rejected_by_component_overlap,
                rejected_by_anchor=rejected_by_anchor,
                rejected_by_confidence=rejected_by_confidence,
                connection_count=len(connections_tuple),
            )
            return connections_tuple

        except ConnectionDetectionError:
            raise
        except Exception as exc:
            logger.error(
                "connection_detection.failed",
                error=str(exc),
                exc_info=True,
            )
            raise ConnectionDetectionError(
                f"Failed to detect connections: {exc}"
            ) from exc

    def _is_line_inside_component(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        components: tuple[DetectedComponent, ...],
    ) -> bool:
        """Check if a line is mostly contained within a component bounding box.

        Args:
            start: Line start point (x, y)
            end: Line end point (x, y)
            components: Tuple of detected components

        Returns:
            True if the line is primarily inside a component bbox (likely a false positive)
        """
        for component in components:
            bbox_x1 = component.x
            bbox_y1 = component.y
            bbox_x2 = component.x + component.width
            bbox_y2 = component.y + component.height

            # Check if both endpoints are inside the same component
            start_inside = (
                bbox_x1 <= start[0] <= bbox_x2 and bbox_y1 <= start[1] <= bbox_y2
            )
            end_inside = (
                bbox_x1 <= end[0] <= bbox_x2 and bbox_y1 <= end[1] <= bbox_y2
            )

            if start_inside and end_inside:
                return True

            if self._line_runs_along_component_border(start, end, component):
                return True

            overlap_ratio = self._line_component_overlap_ratio(start, end, component)
            if overlap_ratio >= self.max_component_overlap_ratio:
                return True

        return False

    def _build_edges(self, gray: np.ndarray) -> np.ndarray:
        """Build edge image with optional morphological cleanup for text/noise suppression."""
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        if not isinstance(blurred, np.ndarray):
            blurred = gray

        edges = cv2.Canny(blurred, self.canny_low, self.canny_high)

        if not isinstance(edges, np.ndarray):
            raise ConnectionDetectionError("Failed to generate edge map from image")

        if self.morphology_kernel_size <= 1:
            return edges

        kernel = np.ones(
            (self.morphology_kernel_size, self.morphology_kernel_size),
            np.uint8,
        )

        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        if not isinstance(closed, np.ndarray):
            return edges

        return closed

    def _line_component_overlap_ratio(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        component: DetectedComponent,
    ) -> float:
        """Estimate how much of a line lies inside a component bounding box."""
        length = self._line_length(start, end)
        if length == 0:
            return 0.0

        sample_count = max(20, int(length // 4))
        inside_count = 0
        for ratio in np.linspace(0.0, 1.0, sample_count):
            x = start[0] + ((end[0] - start[0]) * float(ratio))
            y = start[1] + ((end[1] - start[1]) * float(ratio))
            if self._is_point_inside_component((x, y), component):
                inside_count += 1

        return inside_count / sample_count

    def _line_runs_along_component_border(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        component: DetectedComponent,
    ) -> bool:
        """Detect lines aligned with component borders to suppress rectangle outline artifacts."""
        x1 = component.x
        y1 = component.y
        x2 = component.x + component.width
        y2 = component.y + component.height
        margin = self.border_margin

        line_dx = end[0] - start[0]
        line_dy = end[1] - start[1]

        if abs(line_dy) <= margin:
            if abs(start[1] - y1) <= margin and abs(end[1] - y1) <= margin:
                return self._segment_overlap_1d(start[0], end[0], x1, x2) >= 0.6
            if abs(start[1] - y2) <= margin and abs(end[1] - y2) <= margin:
                return self._segment_overlap_1d(start[0], end[0], x1, x2) >= 0.6

        if abs(line_dx) <= margin:
            if abs(start[0] - x1) <= margin and abs(end[0] - x1) <= margin:
                return self._segment_overlap_1d(start[1], end[1], y1, y2) >= 0.6
            if abs(start[0] - x2) <= margin and abs(end[0] - x2) <= margin:
                return self._segment_overlap_1d(start[1], end[1], y1, y2) >= 0.6

        return False

    def _segment_overlap_1d(
        self,
        a1: float,
        a2: float,
        b1: float,
        b2: float,
    ) -> float:
        """Compute overlap ratio between two 1D segments."""
        seg_a_min, seg_a_max = min(a1, a2), max(a1, a2)
        seg_b_min, seg_b_max = min(b1, b2), max(b1, b2)
        overlap = max(0.0, min(seg_a_max, seg_b_max) - max(seg_a_min, seg_b_min))
        seg_a_len = max(seg_a_max - seg_a_min, 1.0)
        return overlap / seg_a_len

    def _is_point_inside_component(
        self,
        point: tuple[float, float],
        component: DetectedComponent,
    ) -> bool:
        """Return whether a point lies inside a component bounding box."""
        return (
            component.x <= point[0] <= component.x + component.width
            and component.y <= point[1] <= component.y + component.height
        )

    def _is_point_anchored_to_any_component(
        self,
        point: tuple[float, float],
        components: tuple[DetectedComponent, ...],
    ) -> bool:
        """Return whether a point is close enough to any component border."""
        for component in components:
            if self._distance_point_to_component(point, component) <= self.anchor_distance_threshold:
                return True
        return False

    def _is_line_anchored(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        components: tuple[DetectedComponent, ...],
    ) -> bool:
        """Validate at least one endpoint has plausible component anchoring."""
        return (
            self._is_point_anchored_to_any_component(start, components)
            or self._is_point_anchored_to_any_component(end, components)
        )

    def _deduplicate_component_pairs(
        self,
        connections: list[DetectedConnection],
    ) -> list[DetectedConnection]:
        """Keep the highest-confidence connections for each component pair."""
        grouped: dict[tuple[int, int], list[DetectedConnection]] = {}
        passthrough: list[DetectedConnection] = []

        for connection in connections:
            source_idx = connection.source_component_index
            target_idx = connection.target_component_index
            if source_idx is None or target_idx is None:
                passthrough.append(connection)
                continue

            key = tuple(sorted((source_idx, target_idx)))
            grouped.setdefault(key, []).append(connection)

        deduplicated: list[DetectedConnection] = []
        for _, grouped_connections in grouped.items():
            grouped_connections.sort(
                key=lambda item: (
                    item.confidence,
                    self._line_length(item.start_point, item.end_point),
                ),
                reverse=True,
            )
            deduplicated.extend(
                grouped_connections[: self.max_connections_per_component_pair]
            )

        deduplicated.extend(passthrough)
        deduplicated.sort(key=lambda item: item.confidence, reverse=True)
        return deduplicated

    def _distance_point_to_component(
        self,
        point: tuple[float, float],
        component: DetectedComponent,
    ) -> float:
        """Compute Euclidean distance from point to component bounding box."""
        edge_dx = max(component.x - point[0], 0.0, point[0] - (component.x + component.width))
        edge_dy = max(component.y - point[1], 0.0, point[1] - (component.y + component.height))
        return math.sqrt((edge_dx * edge_dx) + (edge_dy * edge_dy))

    def _deduplicate_lines(
        self,
        lines: Iterable[tuple[float, float, float, float]],
    ) -> list[tuple[float, float, float, float]]:
        """Merge near-duplicate Hough lines to avoid inflated connection counts."""
        sorted_lines = sorted(
            lines,
            key=lambda line: self._line_length((line[0], line[1]), (line[2], line[3])),
            reverse=True,
        )
        deduplicated: list[tuple[float, float, float, float]] = []

        for line in sorted_lines:
            if any(self._lines_are_similar(line, kept) for kept in deduplicated):
                continue
            deduplicated.append(line)

        return deduplicated

    def _lines_are_similar(
        self,
        line_a: tuple[float, float, float, float],
        line_b: tuple[float, float, float, float],
    ) -> bool:
        """Return whether two lines represent the same geometric segment."""
        start_a = (line_a[0], line_a[1])
        end_a = (line_a[2], line_a[3])
        start_b = (line_b[0], line_b[1])
        end_b = (line_b[2], line_b[3])

        angle_a = self._line_angle_degrees(start_a, end_a)
        angle_b = self._line_angle_degrees(start_b, end_b)
        angle_diff = abs(angle_a - angle_b)
        angle_diff = min(angle_diff, 180.0 - angle_diff)

        if angle_diff > self.dedup_angle_tolerance:
            return False

        direct_match = (
            self._distance(start_a, start_b) <= self.dedup_endpoint_tolerance
            and self._distance(end_a, end_b) <= self.dedup_endpoint_tolerance
        )
        reverse_match = (
            self._distance(start_a, end_b) <= self.dedup_endpoint_tolerance
            and self._distance(end_a, start_b) <= self.dedup_endpoint_tolerance
        )

        return direct_match or reverse_match

    def _distance(self, p1: tuple[float, float], p2: tuple[float, float]) -> float:
        """Return Euclidean distance between two points."""
        return math.sqrt(((p1[0] - p2[0]) ** 2) + ((p1[1] - p2[1]) ** 2))

    def _line_length(self, start: tuple[float, float], end: tuple[float, float]) -> float:
        """Return Euclidean line length."""
        return self._distance(start, end)

    def _line_angle_degrees(self, start: tuple[float, float], end: tuple[float, float]) -> float:
        """Return line angle in degrees normalized to [0, 180)."""
        angle = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))
        return (angle + 180.0) % 180.0

    def _classify_connection_type(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        edges: np.ndarray,
        arrow_evidence: bool = False,
    ) -> ConnectionType:
        """Classify the type of connection based on geometry.

        Args:
            start: Connection start point (x, y)
            end: Connection end point (x, y)
            edges: Edge-detected image

        Returns:
            ConnectionType enum value
        """
        if arrow_evidence:
            return ConnectionType.ARROW

        length = self._line_length(start, end)
        continuity = self._sample_edge_continuity(start, end, edges)

        if length >= 140.0 and continuity >= 0.55:
            return ConnectionType.ARROW

        return ConnectionType.STRAIGHT

    def _calculate_confidence(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        edges: np.ndarray,
        components: tuple[DetectedComponent, ...],
        source_component_index: int | None,
        target_component_index: int | None,
        arrow_evidence: bool,
    ) -> float:
        """Calculate confidence score for a detected connection.

        Args:
            start: Connection start point (x, y)
            end: Connection end point (x, y)
            edges: Edge-detected image

        Returns:
            Confidence score between 0.0 and 1.0
        """
        length = self._line_length(start, end)
        length_score = min(length / 260.0, 1.0)
        continuity_score = self._sample_edge_continuity(start, end, edges)

        anchored_endpoint_count = 0
        if source_component_index is not None:
            anchored_endpoint_count += 1
        if target_component_index is not None:
            anchored_endpoint_count += 1
        anchor_score = anchored_endpoint_count / 2.0

        overlap_penalty = 0.0
        for component in components:
            overlap_penalty = max(
                overlap_penalty,
                self._line_component_overlap_ratio(start, end, component),
            )

        confidence = (
            0.30
            + (0.30 * continuity_score)
            + (0.20 * length_score)
            + (0.15 * anchor_score)
            + (0.10 if arrow_evidence else 0.0)
            - (0.35 * overlap_penalty)
        )

        if components and anchored_endpoint_count == 0 and not arrow_evidence:
            confidence -= 0.15

        return max(0.0, min(confidence, 1.0))

    def _sample_edge_continuity(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        edges: np.ndarray,
    ) -> float:
        """Estimate line continuity as ratio of sampled points with edge support."""
        if not isinstance(edges, np.ndarray) or edges.ndim != 2:
            return 0.0

        sample_count = max(12, int(self._line_length(start, end) // 6))
        if sample_count <= 0:
            return 0.0

        height, width = edges.shape
        edge_hits = 0

        for ratio in np.linspace(0.0, 1.0, sample_count):
            x = int(round(start[0] + ((end[0] - start[0]) * float(ratio))))
            y = int(round(start[1] + ((end[1] - start[1]) * float(ratio))))
            if 0 <= x < width and 0 <= y < height and edges[y, x] > 0:
                edge_hits += 1

        return edge_hits / sample_count

    def _has_arrowhead(
        self,
        tail: tuple[float, float],
        tip: tuple[float, float],
        edges: np.ndarray,
    ) -> bool:
        """Detect arrowhead evidence near a line endpoint using local branch geometry."""
        if not isinstance(edges, np.ndarray) or edges.ndim != 2:
            return False

        direction_x = tip[0] - tail[0]
        direction_y = tip[1] - tail[1]
        direction_norm = math.sqrt((direction_x * direction_x) + (direction_y * direction_y))
        if direction_norm < 20.0:
            return False

        direction_x /= direction_norm
        direction_y /= direction_norm
        normal_x = -direction_y
        normal_y = direction_x

        radius = self.arrow_window_size
        tip_x = int(round(tip[0]))
        tip_y = int(round(tip[1]))

        y_min = max(0, tip_y - radius)
        y_max = min(edges.shape[0], tip_y + radius + 1)
        x_min = max(0, tip_x - radius)
        x_max = min(edges.shape[1], tip_x + radius + 1)

        roi = edges[y_min:y_max, x_min:x_max]
        if roi.size == 0:
            return False

        ys, xs = np.where(roi > 0)
        if len(xs) < 8:
            return False

        rel_x = (xs + x_min) - tip[0]
        rel_y = (ys + y_min) - tip[1]
        projection = (rel_x * direction_x) + (rel_y * direction_y)
        lateral = (rel_x * normal_x) + (rel_y * normal_y)

        behind_mask = (projection <= -1.0) & (projection >= -float(radius))
        if np.count_nonzero(behind_mask) < 6:
            return False

        left_count = np.count_nonzero(behind_mask & (lateral <= -2.0))
        right_count = np.count_nonzero(behind_mask & (lateral >= 2.0))
        ahead_count = np.count_nonzero(projection > 1.0)

        return left_count >= 2 and right_count >= 2 and ahead_count <= (left_count + right_count)

    def _find_nearest_component(
        self,
        point: tuple[float, float],
        components: tuple[DetectedComponent, ...],
    ) -> int | None:
        """Find the nearest component to a point based on proximity threshold.

        Args:
            point: Point (x, y) to find nearest component for
            components: Tuple of detected components

        Returns:
            Index of nearest component, or None if no component within threshold
        """
        if not components:
            return None

        min_distance = float("inf")
        nearest_idx = None

        for idx, component in enumerate(components):
            # Calculate distance to component center
            comp_center_x = component.x + component.width / 2
            comp_center_y = component.y + component.height / 2

            dx = point[0] - comp_center_x
            dy = point[1] - comp_center_y
            distance = math.sqrt(dx * dx + dy * dy)

            # Also consider distance to component edges
            edge_distance = self._distance_point_to_component(point, component)

            # Use the minimum of center and edge distance
            effective_distance = min(distance, edge_distance * 1.5)

            if effective_distance < min_distance:
                min_distance = effective_distance
                nearest_idx = idx

        # Only return if within proximity threshold
        if min_distance <= self.proximity_threshold:
            return nearest_idx

        return None
