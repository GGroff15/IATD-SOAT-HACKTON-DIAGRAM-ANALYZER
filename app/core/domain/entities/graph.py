from dataclasses import dataclass, field
from uuid import UUID

from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType


@dataclass(frozen=True)
class GraphNode:
    """Represents a graph node derived from a detected component."""

    node_id: int
    component: DetectedComponent

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, int) or self.node_id < 0:
            raise ValueError("node_id must be a non-negative integer")
        if not isinstance(self.component, DetectedComponent):
            raise TypeError("component must be a DetectedComponent")


@dataclass(frozen=True)
class GraphEdge:
    """Represents a graph edge derived from a detected connection."""

    edge_id: int
    connection_type: ConnectionType
    confidence: float
    start_point: tuple[float, float]
    end_point: tuple[float, float]
    source_node_id: int | None = None
    target_node_id: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.edge_id, int) or self.edge_id < 0:
            raise ValueError("edge_id must be a non-negative integer")
        if not isinstance(self.connection_type, ConnectionType):
            raise TypeError("connection_type must be a ConnectionType")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not isinstance(self.start_point, tuple) or len(self.start_point) != 2:
            raise TypeError("start_point must be a tuple of two floats")
        if not isinstance(self.end_point, tuple) or len(self.end_point) != 2:
            raise TypeError("end_point must be a tuple of two floats")
        if self.start_point[0] < 0 or self.start_point[1] < 0:
            raise ValueError("start_point coordinates must be non-negative")
        if self.end_point[0] < 0 or self.end_point[1] < 0:
            raise ValueError("end_point coordinates must be non-negative")
        if self.source_node_id is not None and self.source_node_id < 0:
            raise ValueError("source_node_id must be non-negative or None")
        if self.target_node_id is not None and self.target_node_id < 0:
            raise ValueError("target_node_id must be non-negative or None")


@dataclass(frozen=True)
class Graph:
    """Graph built from detected components and connections."""

    diagram_upload_id: UUID
    nodes: tuple[GraphNode, ...] = field(default_factory=tuple)
    edges: tuple[GraphEdge, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.diagram_upload_id, UUID):
            raise TypeError("diagram_upload_id must be a UUID")
        if not isinstance(self.nodes, tuple):
            raise TypeError("nodes must be a tuple")
        if not isinstance(self.edges, tuple):
            raise TypeError("edges must be a tuple")

        node_ids: set[int] = set()
        for node in self.nodes:
            if not isinstance(node, GraphNode):
                raise TypeError("all nodes must be GraphNode instances")
            if node.node_id in node_ids:
                raise ValueError("node_id values must be unique")
            node_ids.add(node.node_id)

        for edge in self.edges:
            if not isinstance(edge, GraphEdge):
                raise TypeError("all edges must be GraphEdge instances")
            if edge.source_node_id is not None and edge.source_node_id not in node_ids:
                raise ValueError("source_node_id must reference an existing node")
            if edge.target_node_id is not None and edge.target_node_id not in node_ids:
                raise ValueError("target_node_id must reference an existing node")

    @property
    def node_count(self) -> int:
        """Return the number of nodes in the graph."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Return the number of edges in the graph."""
        return len(self.edges)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            f"Graph(diagram_upload_id={self.diagram_upload_id!s}, "
            f"node_count={self.node_count}, edge_count={self.edge_count})"
        )
