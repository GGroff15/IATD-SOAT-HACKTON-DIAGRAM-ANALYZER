from uuid import uuid4, UUID
import pytest

from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import (
    ConnectionType,
    DetectedConnection,
)
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult


def test_diagram_analysis_result_valid_empty():
    uid = uuid4()
    result = DiagramAnalysisResult(diagram_upload_id=uid, components=tuple())
    assert result.diagram_upload_id == uid
    assert result.components == tuple()
    assert result.component_count == 0


def test_diagram_analysis_result_valid_with_components():
    uid = uuid4()
    component1 = DetectedComponent(
        class_name="person",
        confidence=0.95,
        x=100.0,
        y=200.0,
        width=50.0,
        height=80.0,
    )
    component2 = DetectedComponent(
        class_name="car",
        confidence=0.87,
        x=300.0,
        y=400.0,
        width=150.0,
        height=100.0,
    )
    
    result = DiagramAnalysisResult(
        diagram_upload_id=uid,
        components=(component1, component2),
    )
    
    assert result.diagram_upload_id == uid
    assert len(result.components) == 2
    assert result.component_count == 2
    assert result.components[0] == component1
    assert result.components[1] == component2


def test_diagram_analysis_result_immutable():
    uid = uuid4()
    result = DiagramAnalysisResult(diagram_upload_id=uid)
    
    with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
        result.diagram_upload_id = uuid4()


def test_diagram_analysis_result_invalid_uuid_type():
    with pytest.raises(TypeError, match="diagram_upload_id must be a UUID"):
        DiagramAnalysisResult(diagram_upload_id="not-a-uuid", components=tuple())


def test_diagram_analysis_result_invalid_uuid_none():
    with pytest.raises(TypeError, match="diagram_upload_id must be a UUID"):
        DiagramAnalysisResult(diagram_upload_id=None, components=tuple())


def test_diagram_analysis_result_components_not_tuple():
    uid = uuid4()
    component = DetectedComponent(
        class_name="person",
        confidence=0.95,
        x=100.0,
        y=200.0,
        width=50.0,
        height=80.0,
    )
    
    # Should raise TypeError if components is not a tuple
    with pytest.raises(TypeError, match="components must be a tuple"):
        DiagramAnalysisResult(diagram_upload_id=uid, components=[component])


def test_diagram_analysis_result_invalid_component_type():
    uid = uuid4()
    
    with pytest.raises(TypeError, match="all components must be DetectedComponent instances"):
        DiagramAnalysisResult(diagram_upload_id=uid, components=("not a component",))


def test_diagram_analysis_result_component_count_property():
    uid = uuid4()
    components = tuple(
        DetectedComponent(
            class_name=f"object_{i}",
            confidence=0.8,
            x=float(i * 10),
            y=float(i * 20),
            width=10.0,
            height=20.0,
        )
        for i in range(5)
    )
    
    result = DiagramAnalysisResult(diagram_upload_id=uid, components=components)
    assert result.component_count == 5
    assert len(result.components) == 5


def test_diagram_analysis_result_valid_empty_connections():
    """Test creating a result with empty connections tuple."""
    uid = uuid4()
    result = DiagramAnalysisResult(diagram_upload_id=uid, components=tuple(), connections=tuple())
    assert result.diagram_upload_id == uid
    assert result.connections == tuple()
    assert result.connection_count == 0


def test_diagram_analysis_result_default_empty_connections():
    """Test that connections defaults to empty tuple when not provided."""
    uid = uuid4()
    result = DiagramAnalysisResult(diagram_upload_id=uid)
    assert result.connections == tuple()
    assert result.connection_count == 0


def test_diagram_analysis_result_valid_with_connections():
    """Test creating a result with connections."""
    uid = uuid4()
    connection1 = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=0.85,
        start_point=(100.0, 200.0),
        end_point=(300.0, 400.0),
        source_component_index=0,
        target_component_index=1,
    )
    connection2 = DetectedConnection(
        connection_type=ConnectionType.STRAIGHT,
        confidence=0.92,
        start_point=(500.0, 600.0),
        end_point=(700.0, 800.0),
    )
    
    result = DiagramAnalysisResult(
        diagram_upload_id=uid,
        connections=(connection1, connection2),
    )
    
    assert result.diagram_upload_id == uid
    assert len(result.connections) == 2
    assert result.connection_count == 2
    assert result.connections[0] == connection1
    assert result.connections[1] == connection2


def test_diagram_analysis_result_with_components_and_connections():
    """Test creating a result with both components and connections."""
    uid = uuid4()
    component1 = DetectedComponent(
        class_name="box",
        confidence=0.95,
        x=100.0,
        y=200.0,
        width=50.0,
        height=80.0,
    )
    component2 = DetectedComponent(
        class_name="circle",
        confidence=0.87,
        x=300.0,
        y=400.0,
        width=150.0,
        height=100.0,
    )
    connection = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=0.9,
        start_point=(150.0, 240.0),
        end_point=(300.0, 450.0),
        source_component_index=0,
        target_component_index=1,
    )
    
    result = DiagramAnalysisResult(
        diagram_upload_id=uid,
        components=(component1, component2),
        connections=(connection,),
    )
    
    assert result.component_count == 2
    assert result.connection_count == 1
    assert result.components[0] == component1
    assert result.components[1] == component2
    assert result.connections[0] == connection


def test_diagram_analysis_result_connections_not_tuple():
    """Test that connections must be a tuple."""
    uid = uuid4()
    connection = DetectedConnection(
        connection_type=ConnectionType.STRAIGHT,
        confidence=0.8,
        start_point=(0.0, 0.0),
        end_point=(100.0, 100.0),
    )
    
    with pytest.raises(TypeError, match="connections must be a tuple"):
        DiagramAnalysisResult(diagram_upload_id=uid, connections=[connection])


def test_diagram_analysis_result_invalid_connection_type():
    """Test that all connections must be DetectedConnection instances."""
    uid = uuid4()
    
    with pytest.raises(TypeError, match="all connections must be DetectedConnection instances"):
        DiagramAnalysisResult(diagram_upload_id=uid, connections=("not a connection",))


def test_diagram_analysis_result_connection_count_property():
    """Test the connection_count property."""
    uid = uuid4()
    connections = tuple(
        DetectedConnection(
            connection_type=ConnectionType.STRAIGHT,
            confidence=0.8,
            start_point=(float(i * 10), float(i * 20)),
            end_point=(float(i * 10 + 100), float(i * 20 + 100)),
        )
        for i in range(3)
    )
    
    result = DiagramAnalysisResult(diagram_upload_id=uid, connections=connections)
    assert result.connection_count == 3
    assert len(result.connections) == 3


def test_diagram_analysis_result_repr_with_connections():
    """Test that __repr__ includes connection_count."""
    uid = uuid4()
    connection = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=0.9,
        start_point=(0.0, 0.0),
        end_point=(100.0, 100.0),
    )
    result = DiagramAnalysisResult(diagram_upload_id=uid, connections=(connection,))
    repr_str = repr(result)
    assert "connection_count" in repr_str
    assert str(uid) in repr_str
