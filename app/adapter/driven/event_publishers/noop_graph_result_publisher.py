import structlog

from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.graph import Graph
from app.core.domain.entities.llm_architecture_analysis import (
    LlmAnalysisErrorMetadata,
    LlmArchitectureAnalysis,
)

logger = structlog.get_logger()


class NoOpGraphResultPublisher:
    async def publish_graph(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
        llm_analysis: LlmArchitectureAnalysis | None,
        llm_error: LlmAnalysisErrorMetadata | None,
    ) -> None:
        logger.info(
            "graph_result.noop_published",
            diagram_upload_id=str(graph.diagram_upload_id),
            node_count=graph.node_count,
            edge_count=graph.edge_count,
            is_valid=validation_result.is_valid,
            violation_count=len(validation_result.violations),
            llm_risk_count=len(llm_analysis.risks) if llm_analysis is not None else 0,
            llm_recommendation_count=(
                len(llm_analysis.recommendations) if llm_analysis is not None else 0
            ),
            llm_error_code=llm_error.code if llm_error is not None else None,
        )
