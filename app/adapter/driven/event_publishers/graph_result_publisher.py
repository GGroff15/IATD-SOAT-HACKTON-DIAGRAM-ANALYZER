import structlog
import pika

from app.core.application.ports.graph_result_publisher import GraphResultPublisher
from app.core.domain.entities.architectural_validation import (
    ArchitecturalValidationResult,
)
from app.core.domain.entities.graph import Graph
from app.core.domain.entities.llm_architecture_analysis import (
    LlmAnalysisErrorMetadata,
    LlmArchitectureAnalysis,
)

logger = structlog.get_logger()


class RabbitMqGraphResultPublisher(GraphResultPublisher):
    def __init__(
        self,
        rabbitmq_host: str,
        rabbitmq_port: int,
        rabbitmq_queue_name: str,
    ) -> None:
        self._rabbitmq_host = rabbitmq_host
        self._rabbitmq_port = rabbitmq_port
        self._rabbitmq_queue_name = rabbitmq_queue_name
    
    async def publish_graph(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
        llm_analysis: LlmArchitectureAnalysis | None,
        llm_error: LlmAnalysisErrorMetadata | None,
    ) -> None:
        """Publish or persist graph, validation, and optional LLM analysis metadata."""

        logger.info(
            "graph_result.rabbitmq_published",
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

        connection = pika.BlockingConnection(pika.ConnectionParameters(self._rabbitmq_host, self._rabbitmq_port))
        channel = connection.channel()
        channel.queue_declare(queue=self._rabbitmq_queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=self._rabbitmq_queue_name,
            body=str(
                {
                    "protocol": str(graph.diagram_upload_id),
                    "risks": [risk for risk in llm_analysis.risks]
                    if llm_analysis is not None
                    else [],
                    "recommendations": [rec for rec in llm_analysis.recommendations]
                    if llm_analysis is not None
                    else [],
                }
            ),
        )
        channel.close()
        connection.close()
