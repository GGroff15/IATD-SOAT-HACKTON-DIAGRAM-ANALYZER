from uuid import uuid4
import pytest

from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType, DetectedConnection
from app.core.domain.entities.graph import Graph, GraphEdge, GraphNode


def test_graph_creates_with_nodes_and_edges():
    """Test that Graph can be created with valid nodes and edges."""
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
    node = GraphNode(node_id=0, component=component)
    edge = GraphEdge(
        edge_id=0,
        connection_type=ConnectionType.ARROW,
        confidence=0.8,
        start_point=(10.0, 20.0),
        end_point=(50.0, 60.0),
        source_node_id=0,
        target_node_id=0,
    )

    # Act
    graph = Graph(
        diagram_upload_id=diagram_id,
        nodes=(node,),
        edges=(edge,),
    )

    # Assert
    assert graph.diagram_upload_id == diagram_id
    assert graph.node_count == 1
    assert graph.edge_count == 1


def test_graph_allows_orphan_edges():
    """Test that Graph allows edges without source or target node ids."""
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
    node = GraphNode(node_id=0, component=component)
    edge = GraphEdge(
        edge_id=1,
        connection_type=ConnectionType.STRAIGHT,
        confidence=0.7,
        start_point=(10.0, 20.0),
        end_point=(50.0, 60.0),
        source_node_id=None,
        target_node_id=None,
    )

    # Act
    graph = Graph(
        diagram_upload_id=diagram_id,
        nodes=(node,),
        edges=(edge,),
    )

    # Assert
    assert graph.edge_count == 1
    assert graph.edges[0].source_node_id is None
    assert graph.edges[0].target_node_id is None


def test_graph_rejects_edge_with_invalid_source_index():
    """Test that Graph rejects edges referencing invalid node ids."""
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
    node = GraphNode(node_id=0, component=component)
    edge = GraphEdge(
        edge_id=0,
        connection_type=ConnectionType.ARROW,
        confidence=0.8,
        start_point=(10.0, 20.0),
        end_point=(50.0, 60.0),
        source_node_id=2,
        target_node_id=0,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="source_node_id must reference an existing node"):
        Graph(
            diagram_upload_id=diagram_id,
            nodes=(node,),
            edges=(edge,),
        )
