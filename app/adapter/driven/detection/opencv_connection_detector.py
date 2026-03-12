import math

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
    ):
        """Initialize the OpenCV connection detector.

        Args:
            line_threshold: Accumulator threshold for Hough Line Transform
            min_line_length: Minimum line length in pixels
            max_line_gap: Maximum gap between line segments to treat as single line
            canny_low: Lower threshold for Canny edge detection
            canny_high: Upper threshold for Canny edge detection
            proximity_threshold: Maximum distance (pixels) to link connection to component
        """
        self.line_threshold = line_threshold
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.proximity_threshold = proximity_threshold

        logger.info(
            "opencv_connection_detector.initializing",
            line_threshold=line_threshold,
            min_line_length=min_line_length,
            max_line_gap=max_line_gap,
            canny_low=canny_low,
            canny_high=canny_high,
            proximity_threshold=proximity_threshold,
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

            # Apply Canny edge detection
            edges = cv2.Canny(gray, self.canny_low, self.canny_high)

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

            # Process detected lines into connections
            connections = []
            for line in lines:
                x1, y1, x2, y2 = line[0]

                # Filter out lines that are mostly inside component bounding boxes
                if self._is_line_inside_component((x1, y1), (x2, y2), components):
                    continue

                # Calculate connection properties
                start_point = (float(x1), float(y1))
                end_point = (float(x2), float(y2))
                connection_type = self._classify_connection_type(start_point, end_point, edges)
                confidence = self._calculate_confidence(start_point, end_point, edges)

                # Link to nearby components
                source_idx = self._find_nearest_component(start_point, components)
                target_idx = self._find_nearest_component(end_point, components)

                connection = DetectedConnection(
                    connection_type=connection_type,
                    confidence=confidence,
                    start_point=start_point,
                    end_point=end_point,
                    source_component_index=source_idx,
                    target_component_index=target_idx,
                )
                connections.append(connection)

            connections_tuple = tuple(connections)
            logger.info(
                "connection_detection.completed",
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

        return False

    def _classify_connection_type(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        edges: np.ndarray,
    ) -> ConnectionType:
        """Classify the type of connection based on geometry.

        Args:
            start: Connection start point (x, y)
            end: Connection end point (x, y)
            edges: Edge-detected image

        Returns:
            ConnectionType enum value
        """
        # For now, classify based on simple heuristics
        # More sophisticated arrow detection could be added later
        
        # Calculate line length and angle
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx * dx + dy * dy)

        # Simple heuristic: longer lines are more likely to be arrows
        # In a real implementation, we could check for arrowheads using contour analysis
        if length > 100:
            return ConnectionType.ARROW
        else:
            return ConnectionType.STRAIGHT

    def _calculate_confidence(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        edges: np.ndarray,
    ) -> float:
        """Calculate confidence score for a detected connection.

        Args:
            start: Connection start point (x, y)
            end: Connection end point (x, y)
            edges: Edge-detected image

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Calculate confidence based on line length and edge strength
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx * dx + dy * dy)

        # Normalize length to a confidence score
        # Longer lines get higher confidence (up to a point)
        length_score = min(length / 200.0, 1.0)

        # Sample edge strength along the line
        # For simplicity, use a fixed confidence based on length
        # In a real implementation, we could sample edge pixels along the line

        # Base confidence starts at 0.6 and increases with length
        confidence = 0.6 + (length_score * 0.3)

        return min(confidence, 1.0)

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
            # Distance to closest edge
            edge_dx = max(component.x - point[0], 0, point[0] - (component.x + component.width))
            edge_dy = max(component.y - point[1], 0, point[1] - (component.y + component.height))
            edge_distance = math.sqrt(edge_dx * edge_dx + edge_dy * edge_dy)

            # Use the minimum of center and edge distance
            effective_distance = min(distance, edge_distance * 1.5)

            if effective_distance < min_distance:
                min_distance = effective_distance
                nearest_idx = idx

        # Only return if within proximity threshold
        if min_distance <= self.proximity_threshold:
            return nearest_idx

        return None
