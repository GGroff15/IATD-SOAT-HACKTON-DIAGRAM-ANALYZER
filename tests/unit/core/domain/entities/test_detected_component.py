import pytest

from app.core.domain.entities.detected_component import DetectedComponent


def test_detected_component_valid():
    component = DetectedComponent(
        class_name="person",
        confidence=0.95,
        x=100.0,
        y=200.0,
        width=50.0,
        height=80.0,
    )
    assert component.class_name == "person"
    assert component.confidence == 0.95
    assert component.x == 100.0
    assert component.y == 200.0
    assert component.width == 50.0
    assert component.height == 80.0


def test_detected_component_immutable():
    component = DetectedComponent(
        class_name="car",
        confidence=0.8,
        x=10.0,
        y=20.0,
        width=30.0,
        height=40.0,
    )
    with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
        component.confidence = 0.9


@pytest.mark.parametrize("class_name", ["", "   ", None])
def test_detected_component_invalid_class_name(class_name):
    with pytest.raises(ValueError, match="class_name must be a non-empty string"):
        DetectedComponent(
            class_name=class_name,
            confidence=0.8,
            x=0.0,
            y=0.0,
            width=10.0,
            height=10.0,
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.5, 2.0])
def test_detected_component_invalid_confidence(confidence):
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        DetectedComponent(
            class_name="object",
            confidence=confidence,
            x=0.0,
            y=0.0,
            width=10.0,
            height=10.0,
        )


def test_detected_component_valid_confidence_boundaries():
    # Test boundary values
    component_min = DetectedComponent(
        class_name="object",
        confidence=0.0,
        x=0.0,
        y=0.0,
        width=10.0,
        height=10.0,
    )
    assert component_min.confidence == 0.0
    
    component_max = DetectedComponent(
        class_name="object",
        confidence=1.0,
        x=0.0,
        y=0.0,
        width=10.0,
        height=10.0,
    )
    assert component_max.confidence == 1.0


@pytest.mark.parametrize("width", [-1.0, -10.0])
def test_detected_component_invalid_width(width):
    with pytest.raises(ValueError, match="width must be non-negative"):
        DetectedComponent(
            class_name="object",
            confidence=0.8,
            x=0.0,
            y=0.0,
            width=width,
            height=10.0,
        )


@pytest.mark.parametrize("height", [-1.0, -10.0])
def test_detected_component_invalid_height(height):
    with pytest.raises(ValueError, match="height must be non-negative"):
        DetectedComponent(
            class_name="object",
            confidence=0.8,
            x=0.0,
            y=0.0,
            width=10.0,
            height=height,
        )


def test_detected_component_zero_dimensions_allowed():
    # Zero dimensions should be allowed (point detection or edge case)
    component = DetectedComponent(
        class_name="object",
        confidence=0.8,
        x=10.0,
        y=20.0,
        width=0.0,
        height=0.0,
    )
    assert component.width == 0.0
    assert component.height == 0.0


def test_detected_component_with_extracted_text():
    """Test that DetectedComponent can store extracted text from OCR."""
    component = DetectedComponent(
        class_name="button",
        confidence=0.9,
        x=100.0,
        y=200.0,
        width=150.0,
        height=50.0,
        extracted_text="Login Button",
    )
    assert component.class_name == "button"
    assert component.extracted_text == "Login Button"


def test_detected_component_without_extracted_text():
    """Test that extracted_text defaults to None when not provided."""
    component = DetectedComponent(
        class_name="icon",
        confidence=0.85,
        x=50.0,
        y=100.0,
        width=30.0,
        height=30.0,
    )
    assert component.extracted_text is None


def test_detected_component_with_empty_extracted_text():
    """Test that empty string is allowed for extracted_text."""
    component = DetectedComponent(
        class_name="label",
        confidence=0.75,
        x=10.0,
        y=20.0,
        width=100.0,
        height=25.0,
        extracted_text="",
    )
    assert component.extracted_text == ""
