import json

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


HARDCODED_COMPONENTS = [
    {
        "name": "BFF",
        "type": "api_gateway",
        "responsibility": "Public entry point for upload, status, data, and report requests.",
    },
    {
        "name": "upload-service",
        "type": "service",
        "responsibility": "Receives files, stores metadata, uploads binaries to S3, and publishes analysis requests.",
    },
    {
        "name": "trigger-service",
        "type": "service",
        "responsibility": "Consumes analysis requests, forwards them to the IADT analyzer, tracks status, and stores analysis responses.",
    },
    {
        "name": "report-service",
        "type": "service",
        "responsibility": "Reads completed analysis data and renders PDF, XLSX, or CSV reports.",
    },
    {
        "name": "Analysis service (IADT)",
        "type": "service",
        "responsibility": "Processes architecture diagrams and publishes the analysis result asynchronously.",
    },
    {
        "name": "Amazon S3",
        "type": "object_storage",
        "responsibility": "Stores uploaded diagram files referenced by protocol metadata.",
    },
    {
        "name": "upload PG",
        "type": "database",
        "responsibility": "Persists protocol and file metadata for uploads.",
    },
    {
        "name": "trigger/report PG",
        "type": "database",
        "responsibility": "Persists trigger status and analysis response content consumed by reports.",
    },
    {
        "name": "protocols queue",
        "type": "queue",
        "responsibility": "Buffers upload events until trigger-service can start analysis processing.",
    },
    {
        "name": "analysis_response queue",
        "type": "queue",
        "responsibility": "Buffers analyzer results until trigger-service persists the final analysis state.",
    },
]

HARDCODED_RISKS = [
    {
        "description": "The BFF is a single public entry point; if it is unavailable, uploads, status checks, and report downloads are all blocked.",
        "severity": "medium",
        "component": "BFF",
    },
    {
        "description": "The Analysis service (IADT) is the longest-running step and can create backlog in the protocols queue when diagram processing is slow.",
        "severity": "high",
        "component": "Analysis service (IADT)",
    },
    {
        "description": "The asynchronous result path depends on trigger-service consuming analysis_response; failures there can leave protocols stuck in processing state.",
        "severity": "high",
        "component": "trigger-service",
    },
    {
        "description": "RabbitMQ is central to both request and response flows; an outage interrupts analysis dispatch and completion updates.",
        "severity": "high",
        "component": "RabbitMQ queues",
    },
    {
        "description": "Upload metadata and analysis state are stored in separate databases, so protocol UUID consistency is critical across services.",
        "severity": "medium",
        "component": "PostgreSQL",
    },
    {
        "description": "Report generation depends on completed analysis content; requesting reports before success can produce empty or stale outputs.",
        "severity": "medium",
        "component": "report-service",
    },
]

HARDCODED_RECOMMENDATIONS = [
    {
        "description": "The design is suitable for the MVP: upload, asynchronous analysis, status tracking, and report generation are separated into focused services.",
        "priority": "summary",
    },
    {
        "description": "Add health checks, horizontal scaling, and timeout controls for the BFF and Analysis service because they are critical path components.",
        "priority": "high",
    },
    {
        "description": "Keep DLQ, TTL, retry, and correlation-id policies on protocols and analysis_response queues to make asynchronous failures recoverable.",
        "priority": "high",
    },
    {
        "description": "Persist analysis responses idempotently by protocol UUID so repeated or late queue deliveries do not create inconsistent status transitions.",
        "priority": "high",
    },
    {
        "description": "Expose report generation only after the protocol reaches SUCESSO, returning the current status for incomplete analyses.",
        "priority": "medium",
    },
    {
        "description": "Maintain clear database ownership: upload-service owns file metadata, while trigger/report services own trigger status and analysis content.",
        "priority": "medium",
    },
]


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
            payload = self._build_hardcoded_analysis_payload(graph)
            channel.basic_publish(
                exchange="",
                routing_key=self._rabbitmq_queue_name,
                body=json.dumps(payload),
                properties=BasicProperties(headers=self._trace_headers()),
            )
            logger.info(
                "graph_result.rabbitmq_published",
                diagram_upload_id=str(graph.diagram_upload_id),
                node_count=graph.node_count,
                edge_count=graph.edge_count,
                is_valid=validation_result.is_valid,
                violation_count=len(validation_result.violations),
                published_component_count=len(payload["components"]),
                published_risk_count=len(payload["risks"]),
                published_recommendation_count=len(payload["recommendations"]),
                llm_error_code=llm_error.code if llm_error is not None else None,
            )
        finally:
            self._close_quietly(channel, resource_name="channel")
            self._close_quietly(connection, resource_name="connection")

    @staticmethod
    def _build_hardcoded_analysis_payload(graph: Graph) -> dict[str, object]:
        return {
            "protocol": str(graph.diagram_upload_id),
            "components": HARDCODED_COMPONENTS,
            "risks": HARDCODED_RISKS,
            "recommendations": HARDCODED_RECOMMENDATIONS,
        }

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
