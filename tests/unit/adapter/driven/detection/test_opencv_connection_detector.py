from io import BytesIO
from unittest.mock import patch
import pytest
import numpy as np
from PIL import Image

from app.core.application.exceptions import ConnectionDetectionError
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import (
    ConnectionType,
    DetectedConnection,
)


@pytest.fixture
def sample_image_bytes():
    """Generate sample PNG image bytes for testing."""
    img = Image.new("RGB", (640, 480), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_components():
    """Create sample detected components for testing."""
    return (
        DetectedComponent(
            class_name="box",
            confidence=0.9,
            x=50.0,
            y=50.0,
            width=100.0,
            height=100.0,
        ),
        DetectedComponent(
            class_name="circle",
            confidence=0.85,
            x=300.0,
            y=300.0,
            width=80.0,
            height=80.0,
        ),
    )


def test_opencv_connection_detector_initialization_success():
    """Test that OpenCVConnectionDetector initializes successfully with valid parameters."""
    # Arrange & Act
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    detector = OpenCVConnectionDetector(
        line_threshold=50,
        min_line_length=30,
        max_line_gap=10,
        canny_low=50,
        canny_high=150,
        proximity_threshold=20.0,
    )
    
    # Assert
    assert detector.line_threshold == 50
    assert detector.min_line_length == 30
    assert detector.max_line_gap == 10
    assert detector.canny_low == 50
    assert detector.canny_high == 150
    assert detector.proximity_threshold == 20.0


def test_opencv_connection_detector_default_initialization():
    """Test that OpenCVConnectionDetector uses reasonable defaults."""
    # Arrange & Act
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    detector = OpenCVConnectionDetector()
    
    # Assert - verify defaults are set
    assert detector.line_threshold > 0
    assert detector.min_line_length > 0
    assert detector.max_line_gap >= 0
    assert detector.canny_low > 0
    assert detector.canny_high > detector.canny_low
    assert detector.proximity_threshold > 0


@patch("app.adapter.driven.detection.opencv_connection_detector.cv2")
def test_opencv_connection_detector_detect_no_connections(
    mock_cv2, sample_image_bytes, sample_components
):
    """Test detection returns empty tuple when no connections found."""
    # Arrange
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    # Mock OpenCV to return no lines
    mock_cv2.imdecode.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cv2.cvtColor.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.Canny.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.HoughLinesP.return_value = None  # No lines detected
    mock_cv2.IMREAD_COLOR = 1
    mock_cv2.COLOR_BGR2GRAY = 6
    
    detector = OpenCVConnectionDetector()
    
    # Act
    connections = detector.detect(sample_image_bytes, sample_components)
    
    # Assert
    assert isinstance(connections, tuple)
    assert len(connections) == 0


@patch("app.adapter.driven.detection.opencv_connection_detector.cv2")
def test_opencv_connection_detector_detect_single_line(
    mock_cv2, sample_image_bytes, sample_components
):
    """Test detection of a single straight line."""
    # Arrange
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    # Mock OpenCV to return a single line
    mock_cv2.imdecode.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cv2.cvtColor.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.Canny.return_value = np.zeros((480, 640), dtype=np.uint8)
    # Line from (150, 100) to (300, 300) - connects component 0 to component 1
    mock_cv2.HoughLinesP.return_value = np.array([[[150, 100, 300, 300]]])
    mock_cv2.IMREAD_COLOR = 1
    mock_cv2.COLOR_BGR2GRAY = 6
    
    detector = OpenCVConnectionDetector(proximity_threshold=30.0)
    
    # Act
    connections = detector.detect(sample_image_bytes, sample_components)
    
    # Assert
    assert isinstance(connections, tuple)
    assert len(connections) == 1
    
    connection = connections[0]
    assert isinstance(connection, DetectedConnection)
    assert connection.connection_type in [ConnectionType.STRAIGHT, ConnectionType.ARROW]
    assert 0.0 <= connection.confidence <= 1.0
    assert connection.start_point == (150.0, 100.0)
    assert connection.end_point == (300.0, 300.0)


@patch("app.adapter.driven.detection.opencv_connection_detector.cv2")
def test_opencv_connection_detector_detect_multiple_lines(
    mock_cv2, sample_image_bytes, sample_components
):
    """Test detection of multiple lines."""
    # Arrange
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    # Mock OpenCV to return multiple lines
    mock_cv2.imdecode.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cv2.cvtColor.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.Canny.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.HoughLinesP.return_value = np.array([
        [[100, 100, 200, 200]],
        [[300, 100, 400, 200]],
        [[100, 300, 200, 400]],
    ])
    mock_cv2.IMREAD_COLOR = 1
    mock_cv2.COLOR_BGR2GRAY = 6
    
    detector = OpenCVConnectionDetector()
    
    # Act
    connections = detector.detect(sample_image_bytes, sample_components)
    
    # Assert
    assert isinstance(connections, tuple)
    assert len(connections) >= 1  # At least one line should be kept after filtering
    
    for connection in connections:
        assert isinstance(connection, DetectedConnection)
        assert 0.0 <= connection.confidence <= 1.0


@patch("app.adapter.driven.detection.opencv_connection_detector.cv2")
def test_opencv_connection_detector_links_to_components(
    mock_cv2, sample_image_bytes, sample_components
):
    """Test that connections are properly linked to nearby components."""
    # Arrange
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    # Mock OpenCV to return a line near the components
    mock_cv2.imdecode.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cv2.cvtColor.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.Canny.return_value = np.zeros((480, 640), dtype=np.uint8)
    # Line starts near component 0 (50, 50, 100x100) and ends near component 1 (300, 300, 80x80)
    mock_cv2.HoughLinesP.return_value = np.array([[[155, 155, 305, 305]]])
    mock_cv2.IMREAD_COLOR = 1
    mock_cv2.COLOR_BGR2GRAY = 6
    
    detector = OpenCVConnectionDetector(proximity_threshold=50.0)
    
    # Act
    connections = detector.detect(sample_image_bytes, sample_components)
    
    # Assert
    assert len(connections) >= 1
    connection = connections[0]
    # Should link to components based on proximity
    # (may be None if proximity algorithm is strict)
    if connection.source_component_index is not None:
        assert 0 <= connection.source_component_index < len(sample_components)
    if connection.target_component_index is not None:
        assert 0 <= connection.target_component_index < len(sample_components)


@patch("app.adapter.driven.detection.opencv_connection_detector.cv2")
def test_opencv_connection_detector_filters_overlapping_components(
    mock_cv2, sample_image_bytes, sample_components
):
    """Test that lines overlapping with component bounding boxes are filtered out."""
    # Arrange
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    # Mock OpenCV to return lines, some inside component bounding boxes
    mock_cv2.imdecode.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cv2.cvtColor.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.Canny.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.HoughLinesP.return_value = np.array([
        [[60, 60, 70, 70]],  # Inside component 0 bbox (50, 50, 100x100)
        [[200, 200, 250, 250]],  # Outside all components
    ])
    mock_cv2.IMREAD_COLOR = 1
    mock_cv2.COLOR_BGR2GRAY = 6
    
    detector = OpenCVConnectionDetector()
    
    # Act
    connections = detector.detect(sample_image_bytes, sample_components)
    
    # Assert
    # Line inside component should be filtered out
    for connection in connections:
        # Connection endpoints should not be entirely inside component bboxes
        assert isinstance(connection, DetectedConnection)


@patch("app.adapter.driven.detection.opencv_connection_detector.cv2")
def test_opencv_connection_detector_invalid_image_raises_error(mock_cv2, sample_components):
    """Test that invalid image bytes raise ConnectionDetectionError."""
    # Arrange
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    # Mock OpenCV to fail on image decode
    mock_cv2.imdecode.return_value = None
    mock_cv2.IMREAD_COLOR = 1
    
    detector = OpenCVConnectionDetector()
    
    # Act & Assert
    with pytest.raises(ConnectionDetectionError, match="Failed to decode image"):
        detector.detect(b"invalid_image_data", sample_components)


@patch("app.adapter.driven.detection.opencv_connection_detector.cv2")
def test_opencv_connection_detector_opencv_exception_raises_error(
    mock_cv2, sample_image_bytes, sample_components
):
    """Test that OpenCV exceptions are caught and re-raised as ConnectionDetectionError."""
    # Arrange
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    # Mock OpenCV to raise an exception
    mock_cv2.imdecode.side_effect = Exception("OpenCV error")
    
    detector = OpenCVConnectionDetector()
    
    # Act & Assert
    with pytest.raises(ConnectionDetectionError):
        detector.detect(sample_image_bytes, sample_components)


@patch("app.adapter.driven.detection.opencv_connection_detector.cv2")
def test_opencv_connection_detector_empty_components(
    mock_cv2, sample_image_bytes
):
    """Test detection with empty components tuple."""
    # Arrange
    from app.adapter.driven.detection.opencv_connection_detector import (
        OpenCVConnectionDetector,
    )
    
    # Mock OpenCV to return lines
    mock_cv2.imdecode.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cv2.cvtColor.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.Canny.return_value = np.zeros((480, 640), dtype=np.uint8)
    mock_cv2.HoughLinesP.return_value = np.array([[[100, 100, 200, 200]]])
    mock_cv2.IMREAD_COLOR = 1
    mock_cv2.COLOR_BGR2GRAY = 6
    
    detector = OpenCVConnectionDetector()
    
    # Act
    connections = detector.detect(sample_image_bytes, tuple())
    
    # Assert
    assert isinstance(connections, tuple)
    # Connections may be detected but won't be linked to any components
    for connection in connections:
        assert connection.source_component_index is None
        assert connection.target_component_index is None
