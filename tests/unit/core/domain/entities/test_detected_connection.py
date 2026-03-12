import pytest

from app.core.domain.entities.detected_connection import (
    ConnectionType,
    DetectedConnection,
)


def test_detected_connection_valid():
    """Test creating a valid detected connection."""
    connection = DetectedConnection(
        connection_type=ConnectionType.STRAIGHT,
        confidence=0.85,
        start_point=(100.0, 200.0),
        end_point=(300.0, 400.0),
        source_component_index=0,
        target_component_index=1,
    )
    assert connection.connection_type == ConnectionType.STRAIGHT
    assert connection.confidence == 0.85
    assert connection.start_point == (100.0, 200.0)
    assert connection.end_point == (300.0, 400.0)
    assert connection.source_component_index == 0
    assert connection.target_component_index == 1


def test_detected_connection_without_component_indices():
    """Test creating a connection without linked components."""
    connection = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=0.75,
        start_point=(50.0, 60.0),
        end_point=(150.0, 160.0),
    )
    assert connection.connection_type == ConnectionType.ARROW
    assert connection.source_component_index is None
    assert connection.target_component_index is None


def test_detected_connection_immutable():
    """Test that DetectedConnection is immutable (frozen dataclass)."""
    connection = DetectedConnection(
        connection_type=ConnectionType.DASHED,
        confidence=0.9,
        start_point=(10.0, 20.0),
        end_point=(30.0, 40.0),
    )
    with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
        connection.confidence = 0.8


@pytest.mark.parametrize("connection_type", ["straight", "arrow", 123, None])
def test_detected_connection_invalid_connection_type(connection_type):
    """Test that invalid connection_type raises TypeError."""
    with pytest.raises(TypeError, match="connection_type must be a ConnectionType enum value"):
        DetectedConnection(
            connection_type=connection_type,
            confidence=0.8,
            start_point=(0.0, 0.0),
            end_point=(10.0, 10.0),
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.5, 2.0, -1.0])
def test_detected_connection_invalid_confidence(confidence):
    """Test that confidence outside [0.0, 1.0] raises ValueError."""
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        DetectedConnection(
            connection_type=ConnectionType.STRAIGHT,
            confidence=confidence,
            start_point=(0.0, 0.0),
            end_point=(10.0, 10.0),
        )


def test_detected_connection_valid_confidence_boundaries():
    """Test boundary values for confidence (0.0 and 1.0)."""
    connection_min = DetectedConnection(
        connection_type=ConnectionType.CURVED,
        confidence=0.0,
        start_point=(0.0, 0.0),
        end_point=(10.0, 10.0),
    )
    assert connection_min.confidence == 0.0
    
    connection_max = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=1.0,
        start_point=(0.0, 0.0),
        end_point=(10.0, 10.0),
    )
    assert connection_max.confidence == 1.0


@pytest.mark.parametrize("start_point", [
    (10.0,),  # Wrong length (1 element)
    (10.0, 20.0, 30.0),  # Wrong length (3 elements)
    [10.0, 20.0],  # List instead of tuple
    "not_a_tuple",  # String
    None,  # None
])
def test_detected_connection_invalid_start_point_type(start_point):
    """Test that invalid start_point type or length raises TypeError."""
    with pytest.raises(TypeError, match="start_point must be a tuple of two floats"):
        DetectedConnection(
            connection_type=ConnectionType.STRAIGHT,
            confidence=0.8,
            start_point=start_point,
            end_point=(10.0, 10.0),
        )


@pytest.mark.parametrize("end_point", [
    (10.0,),  # Wrong length (1 element)
    (10.0, 20.0, 30.0),  # Wrong length (3 elements)
    [10.0, 20.0],  # List instead of tuple
    "not_a_tuple",  # String
    None,  # None
])
def test_detected_connection_invalid_end_point_type(end_point):
    """Test that invalid end_point type or length raises TypeError."""
    with pytest.raises(TypeError, match="end_point must be a tuple of two floats"):
        DetectedConnection(
            connection_type=ConnectionType.STRAIGHT,
            confidence=0.8,
            start_point=(0.0, 0.0),
            end_point=end_point,
        )


@pytest.mark.parametrize("start_point", [
    (-10.0, 20.0),  # Negative x
    (10.0, -20.0),  # Negative y
    (-10.0, -20.0),  # Both negative
])
def test_detected_connection_negative_start_point_coordinates(start_point):
    """Test that negative start_point coordinates raise ValueError."""
    with pytest.raises(ValueError, match="start_point coordinates must be non-negative"):
        DetectedConnection(
            connection_type=ConnectionType.STRAIGHT,
            confidence=0.8,
            start_point=start_point,
            end_point=(10.0, 10.0),
        )


@pytest.mark.parametrize("end_point", [
    (-10.0, 20.0),  # Negative x
    (10.0, -20.0),  # Negative y
    (-10.0, -20.0),  # Both negative
])
def test_detected_connection_negative_end_point_coordinates(end_point):
    """Test that negative end_point coordinates raise ValueError."""
    with pytest.raises(ValueError, match="end_point coordinates must be non-negative"):
        DetectedConnection(
            connection_type=ConnectionType.STRAIGHT,
            confidence=0.8,
            start_point=(0.0, 0.0),
            end_point=end_point,
        )


@pytest.mark.parametrize("index", [-1, -10, -100])
def test_detected_connection_negative_source_component_index(index):
    """Test that negative source_component_index raises ValueError."""
    with pytest.raises(ValueError, match="source_component_index must be non-negative or None"):
        DetectedConnection(
            connection_type=ConnectionType.ARROW,
            confidence=0.8,
            start_point=(0.0, 0.0),
            end_point=(10.0, 10.0),
            source_component_index=index,
        )


@pytest.mark.parametrize("index", [-1, -10, -100])
def test_detected_connection_negative_target_component_index(index):
    """Test that negative target_component_index raises ValueError."""
    with pytest.raises(ValueError, match="target_component_index must be non-negative or None"):
        DetectedConnection(
            connection_type=ConnectionType.ARROW,
            confidence=0.8,
            start_point=(0.0, 0.0),
            end_point=(10.0, 10.0),
            target_component_index=index,
        )


@pytest.mark.parametrize("index", [0, 1, 5, 100])
def test_detected_connection_valid_component_indices(index):
    """Test that non-negative component indices are valid."""
    connection = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=0.8,
        start_point=(0.0, 0.0),
        end_point=(10.0, 10.0),
        source_component_index=index,
        target_component_index=index,
    )
    assert connection.source_component_index == index
    assert connection.target_component_index == index


@pytest.mark.parametrize("connection_type", [
    ConnectionType.STRAIGHT,
    ConnectionType.DASHED,
    ConnectionType.CURVED,
    ConnectionType.ARROW,
])
def test_detected_connection_all_connection_types(connection_type):
    """Test that all ConnectionType enum values are accepted."""
    connection = DetectedConnection(
        connection_type=connection_type,
        confidence=0.8,
        start_point=(0.0, 0.0),
        end_point=(100.0, 100.0),
    )
    assert connection.connection_type == connection_type


def test_detected_connection_zero_coordinates_allowed():
    """Test that zero coordinates are valid."""
    connection = DetectedConnection(
        connection_type=ConnectionType.STRAIGHT,
        confidence=0.8,
        start_point=(0.0, 0.0),
        end_point=(0.0, 0.0),
    )
    assert connection.start_point == (0.0, 0.0)
    assert connection.end_point == (0.0, 0.0)


def test_detected_connection_repr():
    """Test that __repr__ provides useful string representation."""
    connection = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=0.92,
        start_point=(50.0, 60.0),
        end_point=(150.0, 160.0),
    )
    repr_str = repr(connection)
    assert "arrow" in repr_str.lower()
    assert "0.92" in repr_str
    assert "(50.0, 60.0)" in repr_str
    assert "(150.0, 160.0)" in repr_str
