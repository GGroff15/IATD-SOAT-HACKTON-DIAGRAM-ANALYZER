from uuid import uuid4

from app.core.application.services.graph_builder_service import GraphBuilderService
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType, DetectedConnection
from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult


def test_graph_builder_creates_nodes_from_components():
    """Test that GraphBuilderService maps components to graph nodes."""
    # Arrange
    diagram_id = uuid4()
    component = DetectedComponent(
        class_name="box",
        confidence=0.9,
        x=10.0,
        y=20.0,
        width=100.0,
        height=50.0,
    )
    analysis_result = DiagramAnalysisResult(
        diagram_upload_id=diagram_id,
        components=(component,),
        connections=tuple(),
    )
    builder = GraphBuilderService()

    # Act
    graph = builder.build(analysis_result)

    # Assert
    assert graph.node_count == 1
    assert graph.nodes[0].node_id == 0
    assert graph.nodes[0].component == component


def test_graph_builder_creates_edges_from_connections():
    """Test that GraphBuilderService maps connections to graph edges."""
    # Arrange
    diagram_id = uuid4()
    component = DetectedComponent(
        class_name="box",
        confidence=0.9,
        x=10.0,
        y=20.0,
        width=100.0,
        height=50.0,
    )
    connection = DetectedConnection(
        connection_type=ConnectionType.ARROW,
        confidence=0.8,
        start_point=(10.0, 20.0),
        end_point=(50.0, 60.0),
        source_component_index=0,
        target_component_index=0,
    )
    analysis_result = DiagramAnalysisResult(
        diagram_upload_id=diagram_id,
        components=(component,),
        connections=(connection,),
    )
    builder = GraphBuilderService()

    # Act
    graph = builder.build(analysis_result)

    # Assert
    assert graph.edge_count == 1
    assert graph.edges[0].source_node_id == 0
    assert graph.edges[0].target_node_id == 0
    assert graph.edges[0].connection_type == connection.connection_type


def test_graph_builder_preserves_orphan_connections():
    """Test that GraphBuilderService keeps orphan connections as null endpoints."""
    # Arrange
    diagram_id = uuid4()
    connection = DetectedConnection(
        connection_type=ConnectionType.STRAIGHT,
        confidence=0.5,
        start_point=(10.0, 20.0),
        end_point=(50.0, 60.0),
        source_component_index=None,
        target_component_index=None,
    )
    analysis_result = DiagramAnalysisResult(
        diagram_upload_id=diagram_id,
        components=tuple(),
        connections=(connection,),
    )
    builder = GraphBuilderService()

    # Act
    graph = builder.build(analysis_result)

    # Assert
    assert graph.edge_count == 1
    assert graph.edges[0].source_node_id is None
    assert graph.edges[0].target_node_id is None
