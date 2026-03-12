"""Integration tests for OpenCV-based connection detection with real image processing."""

from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from app.adapter.driven.detection.opencv_connection_detector import (
    OpenCVConnectionDetector,
)
from app.core.application.exceptions import ConnectionDetectionError
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import (
    ConnectionType,
    DetectedConnection,
)


def create_test_image_with_lines(width: int = 640, height: int = 480) -> bytes:
    """Create a test image with drawn lines for connection detection.

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        PNG image bytes
    """
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Draw some lines
    draw.line([(100, 100), (300, 100)], fill="black", width=3)  # Horizontal line
    draw.line([(100, 200), (100, 400)], fill="black", width=3)  # Vertical line
    draw.line([(300, 200), (500, 400)], fill="black", width=3)  # Diagonal line

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_test_image_with_connection(
    start: tuple[int, int],
    end: tuple[int, int],
    width: int = 640,
    height: int = 480,
) -> bytes:
    """Create a test image with a single line connecting two points.

    Args:
        start: Starting point (x, y)
        end: Ending point (x, y)
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        PNG image bytes
    """
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    draw.line([start, end], fill="black", width=3)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_blank_image(width: int = 640, height: int = 480) -> bytes:
    """Create a blank white test image.

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        PNG image bytes
    """
    img = Image.new("RGB", (width, height), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_opencv_connection_detector_real_initialization():
    """Test that OpenCVConnectionDetector initializes with real OpenCV."""
    detector = OpenCVConnectionDetector(
        line_threshold=50,
        min_line_length=30,
        max_line_gap=10,
        canny_low=50,
        canny_high=150,
        proximity_threshold=20.0,
    )

    assert detector.line_threshold == 50
    assert detector.min_line_length == 30


def test_opencv_connection_detector_detect_blank_image():
    """Test that blank image returns no connections."""
    detector = OpenCVConnectionDetector()
    image_bytes = create_blank_image()

    connections = detector.detect(image_bytes, tuple())

    assert isinstance(connections, tuple)
    assert len(connections) == 0


def test_opencv_connection_detector_detect_simple_lines():
    """Test detection of simple drawn lines in a real image."""
    detector = OpenCVConnectionDetector(
        line_threshold=40,
        min_line_length=50,
        canny_low=50,
        canny_high=150,
    )
    image_bytes = create_test_image_with_lines()

    connections = detector.detect(image_bytes, tuple())

    # Should detect at least one line
    assert isinstance(connections, tuple)
    assert len(connections) > 0

    # Verify connection properties
    for connection in connections:
        assert isinstance(connection, DetectedConnection)
        assert connection.connection_type in [
            ConnectionType.STRAIGHT,
            ConnectionType.ARROW,
            ConnectionType.DASHED,
            ConnectionType.CURVED,
        ]
        assert 0.0 <= connection.confidence <= 1.0
        assert connection.start_point[0] >= 0
        assert connection.start_point[1] >= 0
        assert connection.end_point[0] >= 0
        assert connection.end_point[1] >= 0


def test_opencv_connection_detector_single_connection():
    """Test detection of a single connection between two points."""
    detector = OpenCVConnectionDetector(
        line_threshold=30,
        min_line_length=100,
        canny_low=50,
        canny_high=150,
    )

    # Create image with single long line
    image_bytes = create_test_image_with_connection((100, 200), (500, 200))

    connections = detector.detect(image_bytes, tuple())

    # Should detect the line
    assert len(connections) >= 1

    # Verify first connection properties
    connection = connections[0]
    assert connection.confidence > 0.0

    # Line endpoints should be approximately correct
    # (OpenCV may not detect exact pixels, allow some tolerance)
    start_x, start_y = connection.start_point
    end_x, end_y = connection.end_point

    # One endpoint should be near (100, 200) and other near (500, 200)
    # (order might be reversed)
    assert (
        (80 <= start_x <= 120 and 180 <= start_y <= 220)
        or (480 <= start_x <= 520 and 180 <= start_y <= 220)
    )


def test_opencv_connection_detector_with_components():
    """Test connection detection with components present."""
    detector = OpenCVConnectionDetector(
        line_threshold=30,
        min_line_length=50,
        proximity_threshold=50.0,
    )

    # Create components at specific locations
    components = (
        DetectedComponent(
            class_name="box1",
            confidence=0.9,
            x=50.0,
            y=150.0,
            width=80.0,
            height=80.0,
        ),
        DetectedComponent(
            class_name="box2",
            confidence=0.9,
            x=450.0,
            y=150.0,
            width=80.0,
            height=80.0,
        ),
    )

    # Create line connecting the two components (roughly)
    # Line from center of box1 to center of box2
    image_bytes = create_test_image_with_connection((130, 190), (490, 190))

    connections = detector.detect(image_bytes, components)

    # Should detect connection(s)
    assert len(connections) >= 1

    # May or may not link depending on proximity - test that indices are valid if present
    for connection in connections:
        if connection.source_component_index is not None:
            assert 0 <= connection.source_component_index < len(components)
        if connection.target_component_index is not None:
            assert 0 <= connection.target_component_index < len(components)


def test_opencv_connection_detector_different_thresholds():
    """Test that different confidence thresholds affect detection results."""
    image_bytes = create_test_image_with_lines()

    # Low threshold - should detect more lines
    detector_low = OpenCVConnectionDetector(
        line_threshold=20,
        min_line_length=30,
    )
    connections_low = detector_low.detect(image_bytes, tuple())

    # High threshold - should detect fewer lines
    detector_high = OpenCVConnectionDetector(
        line_threshold=100,
        min_line_length=100,
    )
    connections_high = detector_high.detect(image_bytes, tuple())

    # Lower threshold should detect at least as many connections
    assert len(connections_low) >= len(connections_high)


def test_opencv_connection_detector_invalid_image_bytes():
    """Test that invalid image bytes raise ConnectionDetectionError."""
    detector = OpenCVConnectionDetector()

    with pytest.raises(ConnectionDetectionError, match="Failed to decode image"):
        detector.detect(b"not_valid_image_data", tuple())


def test_opencv_connection_detector_empty_image_bytes():
    """Test that empty image bytes raise ConnectionDetectionError."""
    detector = OpenCVConnectionDetector()

    with pytest.raises(ConnectionDetectionError):
        detector.detect(b"", tuple())


def test_opencv_connection_detector_corrupted_png():
    """Test that corrupted PNG data raises ConnectionDetectionError."""
    detector = OpenCVConnectionDetector()

    # Create invalid PNG header
    corrupted_png = b"\x89PNG\r\n\x1a\n" + b"corrupted_data"

    with pytest.raises(ConnectionDetectionError):
        detector.detect(corrupted_png, tuple())


def test_opencv_connection_detector_with_empty_components():
    """Test that detection works with empty components tuple."""
    detector = OpenCVConnectionDetector()
    image_bytes = create_test_image_with_lines()

    connections = detector.detect(image_bytes, tuple())

    # Should still detect connections
    assert isinstance(connections, tuple)

    # All connections should have None component indices
    for connection in connections:
        assert connection.source_component_index is None
        assert connection.target_component_index is None


def test_opencv_connection_detector_proximity_threshold():
    """Test that proximity threshold affects component linking."""
    components = (
        DetectedComponent(
            class_name="box1",
            confidence=0.9,
            x=50.0,
            y=150.0,
            width=80.0,
            height=80.0,
        ),
    )

    # Line far from component
    image_bytes = create_test_image_with_connection((400, 400), (500, 450))

    # Very strict proximity threshold
    detector_strict = OpenCVConnectionDetector(
        line_threshold=30,
        min_line_length=50,
        proximity_threshold=10.0,
    )
    connections_strict = detector_strict.detect(image_bytes, components)

    # Relaxed proximity threshold
    detector_relaxed = OpenCVConnectionDetector(
        line_threshold=30,
        min_line_length=50,
        proximity_threshold=500.0,
    )
    connections_relaxed = detector_relaxed.detect(image_bytes, components)

    # Both should detect connections
    assert len(connections_strict) > 0
    assert len(connections_relaxed) > 0

    # Strict should have fewer linked connections
    strict_linked = sum(
        1 for c in connections_strict
        if c.source_component_index is not None or c.target_component_index is not None
    )
    relaxed_linked = sum(
        1 for c in connections_relaxed
        if c.source_component_index is not None or c.target_component_index is not None
    )

    assert relaxed_linked >= strict_linked
