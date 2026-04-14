import structlog

from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.graph import Graph

logger = structlog.get_logger()


class NoOpGraphResultPublisher:
    async def publish_graph(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
    ) -> None:
        logger.info(
            "graph_result.noop_published",
            diagram_upload_id=str(graph.diagram_upload_id),
            node_count=graph.node_count,
            edge_count=graph.edge_count,
            is_valid=validation_result.is_valid,
            violation_count=len(validation_result.violations),
        )