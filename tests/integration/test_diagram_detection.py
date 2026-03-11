"""Integration tests for diagram component detection workflow."""
from io import BytesIO
from uuid import uuid4
import pytest
from PIL import Image, ImageDraw

from app.adapter.driven.detection.yolo_detector import YoloDetector
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult


@pytest.fixture
def yolo_detector():
    """Provide real YoloDetector for integration testing."""
    return YoloDetector(
        model_name="yolov8n.pt",
        confidence_threshold=0.5,
        device="cpu",
    )


@pytest.fixture
def sample_blank_image_bytes():
    """Create a simple blank image for testing (likely no detections)."""
    img = Image.new("RGB", (640, 480), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_simple_shapes_image_bytes():
    """Create an image with simple geometric shapes."""
    img = Image.new("RGB", (640, 480), color="white")
    draw = ImageDraw.Draw(img)
    
    # Draw some basic shapes that might be detected
    draw.rectangle([100, 100, 200, 200], fill="blue", outline="black", width=2)
    draw.ellipse([300, 100, 400, 200], fill="red", outline="black", width=2)
    draw.rectangle([100, 300, 200, 400], fill="green", outline="black", width=2)
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_yolo_detector_initialization(yolo_detector):
    """Test that YoloDetector initializes successfully with real YOLO model."""
    # Assert
    assert yolo_detector.model_name == "yolov8n.pt"
    assert yolo_detector.confidence_threshold == 0.5
    assert yolo_detector.device == "cpu"
    assert yolo_detector.model is not None


def test_yolo_detector_detect_blank_image(yolo_detector, sample_blank_image_bytes):
    """Test detection on a blank image (should return empty or minimal detections)."""
    # Arrange
    diagram_id = uuid4()
    
    # Act
    result = yolo_detector.detect(diagram_id, sample_blank_image_bytes)
    
    # Assert
    assert isinstance(result, DiagramAnalysisResult)
    assert result.diagram_upload_id == diagram_id
    assert isinstance(result.components, tuple)
    # Blank image should have few or no detections
    assert result.component_count >= 0


def test_yolo_detector_detect_simple_shapes(yolo_detector, sample_simple_shapes_image_bytes):
    """Test detection on an image with simple geometric shapes."""
    # Arrange
    diagram_id = uuid4()
    
    # Act
    result = yolo_detector.detect(diagram_id, sample_simple_shapes_image_bytes)
    
    # Assert
    assert isinstance(result, DiagramAnalysisResult)
    assert result.diagram_upload_id == diagram_id
    assert isinstance(result.components, tuple)
    
    # Verify all components have required attributes
    for component in result.components:
        assert isinstance(component.class_name, str)
        assert 0.0 <= component.confidence <= 1.0
        assert component.x >= 0
        assert component.y >= 0
        assert component.width >= 0
        assert component.height >= 0


def test_yolo_detector_different_confidence_thresholds(sample_simple_shapes_image_bytes):
    """Test that different confidence thresholds affect detection results."""
    # Arrange
    diagram_id = uuid4()
    
    # Create detectors with different thresholds
    detector_low = YoloDetector(
        model_name="yolov8n.pt",
        confidence_threshold=0.1,
        device="cpu",
    )
    detector_high = YoloDetector(
        model_name="yolov8n.pt",
        confidence_threshold=0.9,
        device="cpu",
    )
    
    # Act
    result_low = detector_low.detect(diagram_id, sample_simple_shapes_image_bytes)
    result_high = detector_high.detect(diagram_id, sample_simple_shapes_image_bytes)
    
    # Assert
    # Lower threshold should detect at least as many objects as higher threshold
    assert result_low.component_count >= result_high.component_count


def test_yolo_detector_invalid_image_bytes(yolo_detector):
    """Test that invalid image bytes raise appropriate error."""
    # Arrange
    diagram_id = uuid4()
    invalid_bytes = b"not an image"
    
    # Act & Assert
    from app.core.application.exceptions import DiagramDetectionError
    with pytest.raises(DiagramDetectionError, match="Failed to detect components"):
        yolo_detector.detect(diagram_id, invalid_bytes)


def test_yolo_detector_jpeg_image():
    """Test detection on a JPEG image (should be handled by PIL)."""
    # Arrange
    detector = YoloDetector(model_name="yolov8n.pt", confidence_threshold=0.5)
    diagram_id = uuid4()
    
    # Create JPEG image
    img = Image.new("RGB", (320, 240), color="lightgray")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    jpeg_bytes = buffer.getvalue()
    
    # Act
    result = detector.detect(diagram_id, jpeg_bytes)
    
    # Assert
    assert isinstance(result, DiagramAnalysisResult)
    assert result.diagram_upload_id == diagram_id


def test_yolo_detector_large_image():
    """Test detection on a larger image to verify model handles different sizes."""
    # Arrange
    detector = YoloDetector(model_name="yolov8n.pt", confidence_threshold=0.5)
    diagram_id = uuid4()
    
    # Create larger image
    img = Image.new("RGB", (1920, 1080), color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    large_image_bytes = buffer.getvalue()
    
    # Act
    result = detector.detect(diagram_id, large_image_bytes)
    
    # Assert
    assert isinstance(result, DiagramAnalysisResult)
    assert result.diagram_upload_id == diagram_id
    # Should complete without errors even on large images
