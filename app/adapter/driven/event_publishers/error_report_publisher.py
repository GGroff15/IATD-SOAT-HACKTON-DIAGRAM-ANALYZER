import structlog
import pika
from pika import BasicProperties

from app.infrastructure.logging.correlation import get_correlation_id
from app.core.application.ports.error_report_payload import ErrorReportPayload
from app.core.application.ports.error_report_publisher import ErrorReportPublisher

logger = structlog.get_logger()


class RabbitMqErrorReportPublisher(ErrorReportPublisher):
    def __init__(
        self,
        rabbitmq_host: str = "localhost",
        rabbitmq_port: int = 5672,
        rabbitmq_queue_name: str = "analysis_response",
        rabbitmq_message_ttl_ms: int = 5000,
        rabbitmq_dlx_exchange_name: str = "analysis_response_dlx_exchange",
        rabbitmq_dlq_queue_name: str = "analysis_response_dlq_queue",
        rabbitmq_dlq_routing_key: str = "analysis_response_dlq_routing_key",
    ) -> None:
        self.rabbitmq_host = rabbitmq_host
        self.rabbitmq_port = rabbitmq_port
        self.rabbitmq_queue_name = rabbitmq_queue_name
        self.rabbitmq_message_ttl_ms = rabbitmq_message_ttl_ms
        self.rabbitmq_dlx_exchange_name = rabbitmq_dlx_exchange_name
        self.rabbitmq_dlq_queue_name = rabbitmq_dlq_queue_name
        self.rabbitmq_dlq_routing_key = rabbitmq_dlq_routing_key

    async def publish_error(self, payload: ErrorReportPayload) -> None:
        connection = None
        channel = None
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(self.rabbitmq_host, self.rabbitmq_port)
            )
            channel = connection.channel()
            self._declare_response_topology(channel)
            channel.basic_publish(
                exchange="",
                routing_key=self.rabbitmq_queue_name,
                body=str(
                    {
                        "protocol": str(payload.correlation_id),
                        "status": "error",
                        "reason": payload.reason,
                    }
                ),
                properties=BasicProperties(headers=self._trace_headers()),
            )
            logger.info(
                "error_report.publish",
                classification=payload.classification,
                path=payload.path,
                timestamp=payload.timestamp,
            )
        finally:
            self._close_quietly(channel, resource_name="channel")
            self._close_quietly(connection, resource_name="connection")

    def _declare_response_topology(self, channel) -> None:
        channel.exchange_declare(
            exchange=self.rabbitmq_dlx_exchange_name,
            exchange_type="direct",
            durable=True,
        )
        channel.queue_declare(
            queue=self.rabbitmq_dlq_queue_name,
            durable=True,
        )
        channel.queue_bind(
            queue=self.rabbitmq_dlq_queue_name,
            exchange=self.rabbitmq_dlx_exchange_name,
            routing_key=self.rabbitmq_dlq_routing_key,
        )
        channel.queue_declare(
            queue=self.rabbitmq_queue_name,
            durable=True,
            arguments={
                "x-message-ttl": self.rabbitmq_message_ttl_ms,
                "x-dead-letter-exchange": self.rabbitmq_dlx_exchange_name,
                "x-dead-letter-routing-key": self.rabbitmq_dlq_routing_key,
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
