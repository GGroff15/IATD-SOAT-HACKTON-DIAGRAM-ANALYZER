from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult
from app.core.domain.entities.graph import Graph, GraphEdge, GraphNode


class GraphBuilderService:
    """Builds a graph from diagram analysis results."""

    def build(self, analysis_result: DiagramAnalysisResult) -> Graph:
        """Build a graph from detected components and connections.

        Args:
            analysis_result: Diagram analysis result with components and connections

        Returns:
            Graph containing nodes and edges derived from the analysis
        """
        nodes = tuple(
            GraphNode(node_id=index, component=component)
            for index, component in enumerate(analysis_result.components)
        )
        edges = tuple(
            GraphEdge(
                edge_id=index,
                connection_type=connection.connection_type,
                confidence=connection.confidence,
                start_point=connection.start_point,
                end_point=connection.end_point,
                source_node_id=connection.source_component_index,
                target_node_id=connection.target_component_index,
            )
            for index, connection in enumerate(analysis_result.connections)
        )
        return Graph(
            diagram_upload_id=analysis_result.diagram_upload_id,
            nodes=nodes,
            edges=edges,
        )
