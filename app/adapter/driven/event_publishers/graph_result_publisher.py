import structlog
import pika
from pika import BasicProperties

from app.infrastructure.logging.correlation import get_correlation_id
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
        rabbitmq_message_ttl_ms: int = 5000,
        rabbitmq_dlx_exchange_name: str = "analysis_response_dlx_exchange",
        rabbitmq_dlq_queue_name: str = "analysis_response_dlq_queue",
        rabbitmq_dlq_routing_key: str = "analysis_response_dlq_routing_key",
    ) -> None:
        self._rabbitmq_host = rabbitmq_host
        self._rabbitmq_port = rabbitmq_port
        self._rabbitmq_queue_name = rabbitmq_queue_name
        self._rabbitmq_message_ttl_ms = rabbitmq_message_ttl_ms
        self._rabbitmq_dlx_exchange_name = rabbitmq_dlx_exchange_name
        self._rabbitmq_dlq_queue_name = rabbitmq_dlq_queue_name
        self._rabbitmq_dlq_routing_key = rabbitmq_dlq_routing_key

    async def publish_graph(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
        llm_analysis: LlmArchitectureAnalysis | None,
        llm_error: LlmAnalysisErrorMetadata | None = None,
    ) -> None:
        """Publish or persist graph, validation, and optional LLM analysis metadata."""

        connection = None
        channel = None
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(self._rabbitmq_host, self._rabbitmq_port)
            )
            channel = connection.channel()
            self._declare_response_topology(channel)
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
                properties=BasicProperties(headers=self._trace_headers()),
            )
            logger.info(
                "graph_result.rabbitmq_published",
                diagram_upload_id=str(graph.diagram_upload_id),
                node_count=graph.node_count,
                edge_count=graph.edge_count,
                is_valid=validation_result.is_valid,
                violation_count=len(validation_result.violations),
                llm_risk_count=len(llm_analysis.risks)
                if llm_analysis is not None
                else 0,
                llm_recommendation_count=(
                    len(llm_analysis.recommendations) if llm_analysis is not None else 0
                ),
                llm_error_code=llm_error.code if llm_error is not None else None,
            )
        finally:
            self._close_quietly(channel, resource_name="channel")
            self._close_quietly(connection, resource_name="connection")

    def _declare_response_topology(self, channel) -> None:
        channel.exchange_declare(
            exchange=self._rabbitmq_dlx_exchange_name,
            exchange_type="direct",
            durable=True,
        )
        channel.queue_declare(
            queue=self._rabbitmq_dlq_queue_name,
            durable=True,
        )
        channel.queue_bind(
            queue=self._rabbitmq_dlq_queue_name,
            exchange=self._rabbitmq_dlx_exchange_name,
            routing_key=self._rabbitmq_dlq_routing_key,
        )
        channel.queue_declare(
            queue=self._rabbitmq_queue_name,
            durable=True,
            arguments={
                "x-message-ttl": self._rabbitmq_message_ttl_ms,
                "x-dead-letter-exchange": self._rabbitmq_dlx_exchange_name,
                "x-dead-letter-routing-key": self._rabbitmq_dlq_routing_key,
            },
        )

    @staticmethod
    def _close_quietly(resource, resource_name: str) -> None:
        if resource is None or not getattr(resource, "is_open", True):
            return

        try:
            resource.close()
        except Exception as error:  # pragma: no cover - defensive cleanup path
            logger.warning(
                "rabbitmq.resource_close_failed",
                resource=resource_name,
                error_type=type(error).__name__,
                error=str(error),
            )

    @staticmethod
    def _trace_headers() -> dict[str, str]:
        headers: dict[str, str] = {}
        correlation_id = get_correlation_id()
        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id
        try:
            from opentelemetry.propagate import inject

            inject(headers)
        except Exception:
            pass
        return headers
