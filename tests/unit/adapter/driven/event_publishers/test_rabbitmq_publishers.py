import json
from uuid import UUID

import pytest

from app.adapter.driven.event_publishers import error_report_publisher as error_module
from app.adapter.driven.event_publishers import graph_result_publisher as graph_module
from app.adapter.driven.event_publishers.error_report_publisher import (
    RabbitMqErrorReportPublisher,
)
from app.adapter.driven.event_publishers.graph_result_publisher import (
    HARDCODED_COMPONENTS,
    HARDCODED_RECOMMENDATIONS,
    HARDCODED_RISKS,
    RabbitMqGraphResultPublisher,
)
from app.core.application.ports.error_report_payload import ErrorReportPayload
from app.core.domain.entities.architectural_validation import (
    ArchitecturalValidationResult,
)
from app.core.domain.entities.graph import Graph
from app.core.domain.entities.llm_architecture_analysis import LlmArchitectureAnalysis


class FakeChannel:
    fail_on_queue: str | None = None

    def __init__(self) -> None:
        self.exchange_declare_calls: list[dict] = []
        self.queue_declare_calls: list[dict] = []
        self.queue_bind_calls: list[dict] = []
        self.basic_publish_calls: list[dict] = []
        self.closed = False

    def exchange_declare(self, **kwargs) -> None:
        self.exchange_declare_calls.append(kwargs)

    def queue_declare(self, **kwargs) -> None:
        self.queue_declare_calls.append(kwargs)
        if kwargs.get("queue") == self.fail_on_queue:
            raise RuntimeError("queue declare failed")

    def queue_bind(self, **kwargs) -> None:
        self.queue_bind_calls.append(kwargs)

    def basic_publish(self, **kwargs) -> None:
        self.basic_publish_calls.append(kwargs)

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    instances: list["FakeConnection"] = []
    channel_class = FakeChannel

    def __init__(self, _parameters) -> None:
        self.channel_instance = self.channel_class()
        self.closed = False
        self.instances.append(self)

    def channel(self) -> FakeChannel:
        return self.channel_instance

    def close(self) -> None:
        self.closed = True


def _patch_blocking_connection(monkeypatch) -> None:
    FakeConnection.instances.clear()
    FakeConnection.channel_class = FakeChannel
    FakeChannel.fail_on_queue = None
    monkeypatch.setattr(graph_module.pika, "BlockingConnection", FakeConnection)
    monkeypatch.setattr(error_module.pika, "BlockingConnection", FakeConnection)


def _successful_graph_payload() -> tuple[
    Graph, ArchitecturalValidationResult, LlmArchitectureAnalysis
]:
    diagram_upload_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    return (
        Graph(diagram_upload_id=diagram_upload_id),
        ArchitecturalValidationResult(
            diagram_upload_id=diagram_upload_id, is_valid=True
        ),
        LlmArchitectureAnalysis(
            risks=("single point of failure",),
            recommendations=("Add redundancy.",),
        ),
    )


def _assert_response_topology_declared(channel: FakeChannel, ttl_ms: int) -> None:
    assert channel.exchange_declare_calls == [
        {
            "exchange": "analysis_response_dlx_exchange",
            "exchange_type": "direct",
            "durable": True,
        }
    ]
    assert channel.queue_declare_calls == [
        {
            "queue": "analysis_response_dlq_queue",
            "durable": True,
        },
        {
            "queue": "analysis_response",
            "durable": True,
            "arguments": {
                "x-message-ttl": ttl_ms,
                "x-dead-letter-exchange": "analysis_response_dlx_exchange",
                "x-dead-letter-routing-key": "analysis_response_dlq_routing_key",
            },
        },
    ]
    assert channel.queue_bind_calls == [
        {
            "queue": "analysis_response_dlq_queue",
            "exchange": "analysis_response_dlx_exchange",
            "routing_key": "analysis_response_dlq_routing_key",
        }
    ]


@pytest.mark.asyncio
async def test_graph_result_publisher_declares_response_queue_with_default_ttl(
    monkeypatch,
) -> None:
    _patch_blocking_connection(monkeypatch)
    graph, validation_result, llm_analysis = _successful_graph_payload()
    publisher = RabbitMqGraphResultPublisher(
        rabbitmq_host="rabbitmq",
        rabbitmq_port=5672,
        rabbitmq_queue_name="analysis_response",
    )

    await publisher.publish_graph(graph, validation_result, llm_analysis)

    connection = FakeConnection.instances[0]
    channel = connection.channel_instance
    _assert_response_topology_declared(channel, ttl_ms=5000)
    assert channel.closed is True
    assert connection.closed is True


@pytest.mark.asyncio
async def test_graph_result_publisher_publishes_hardcoded_analysis_payload(
    monkeypatch,
) -> None:
    _patch_blocking_connection(monkeypatch)
    graph, validation_result, llm_analysis = _successful_graph_payload()
    publisher = RabbitMqGraphResultPublisher(
        rabbitmq_host="rabbitmq",
        rabbitmq_port=5672,
        rabbitmq_queue_name="analysis_response",
    )

    await publisher.publish_graph(graph, validation_result, llm_analysis)

    channel = FakeConnection.instances[0].channel_instance
    assert len(channel.basic_publish_calls) == 1

    publish_call = channel.basic_publish_calls[0]
    payload = json.loads(publish_call["body"])
    assert publish_call["exchange"] == ""
    assert publish_call["routing_key"] == "analysis_response"
    assert payload == {
        "protocol": "550e8400-e29b-41d4-a716-446655440000",
        "components": HARDCODED_COMPONENTS,
        "risks": HARDCODED_RISKS,
        "recommendations": HARDCODED_RECOMMENDATIONS,
    }


@pytest.mark.asyncio
async def test_graph_result_publisher_closes_connection_when_declare_fails(
    monkeypatch,
) -> None:
    _patch_blocking_connection(monkeypatch)
    FakeConnection.channel_class = type(
        "FailingChannel",
        (FakeChannel,),
        {"fail_on_queue": "analysis_response"},
    )
    graph, validation_result, llm_analysis = _successful_graph_payload()
    publisher = RabbitMqGraphResultPublisher(
        rabbitmq_host="rabbitmq",
        rabbitmq_port=5672,
        rabbitmq_queue_name="analysis_response",
    )

    with pytest.raises(RuntimeError, match="queue declare failed"):
        await publisher.publish_graph(graph, validation_result, llm_analysis)

    connection = FakeConnection.instances[0]
    channel = FakeConnection.instances[0].channel_instance
    assert channel.closed is True
    assert connection.closed is True


@pytest.mark.asyncio
async def test_error_report_publisher_declares_response_queue_with_default_ttl(
    monkeypatch,
) -> None:
    _patch_blocking_connection(monkeypatch)
    publisher = RabbitMqErrorReportPublisher(
        rabbitmq_host="rabbitmq",
        rabbitmq_port=5672,
        rabbitmq_queue_name="analysis_response",
    )

    await publisher.publish_error(
        ErrorReportPayload(
            classification="processing-error",
            reason="failed",
            path="/processing-start",
            timestamp="2026-05-17T14:00:00Z",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
        )
    )

    connection = FakeConnection.instances[0]
    channel = connection.channel_instance
    _assert_response_topology_declared(channel, ttl_ms=5000)
    assert channel.closed is True
    assert connection.closed is True


@pytest.mark.asyncio
async def test_error_report_publisher_closes_connection_when_declare_fails(
    monkeypatch,
) -> None:
    _patch_blocking_connection(monkeypatch)
    FakeConnection.channel_class = type(
        "FailingChannel",
        (FakeChannel,),
        {"fail_on_queue": "analysis_response"},
    )
    publisher = RabbitMqErrorReportPublisher(
        rabbitmq_host="rabbitmq",
        rabbitmq_port=5672,
        rabbitmq_queue_name="analysis_response",
    )

    with pytest.raises(RuntimeError, match="queue declare failed"):
        await publisher.publish_error(
            ErrorReportPayload(
                classification="processing-error",
                reason="failed",
                path="/processing-start",
                timestamp="2026-05-17T14:00:00Z",
                correlation_id="550e8400-e29b-41d4-a716-446655440000",
            )
        )

    connection = FakeConnection.instances[0]
    channel = connection.channel_instance
    assert channel.closed is True
    assert connection.closed is True


@pytest.mark.asyncio
async def test_graph_result_publisher_uses_configured_ttl(monkeypatch) -> None:
    _patch_blocking_connection(monkeypatch)
    graph, validation_result, llm_analysis = _successful_graph_payload()
    publisher = RabbitMqGraphResultPublisher(
        rabbitmq_host="rabbitmq",
        rabbitmq_port=5672,
        rabbitmq_queue_name="analysis_response",
        rabbitmq_message_ttl_ms=12345,
    )

    await publisher.publish_graph(graph, validation_result, llm_analysis)

    channel = FakeConnection.instances[0].channel_instance
    _assert_response_topology_declared(channel, ttl_ms=12345)


@pytest.mark.asyncio
async def test_error_report_publisher_uses_configured_ttl(monkeypatch) -> None:
    _patch_blocking_connection(monkeypatch)
    publisher = RabbitMqErrorReportPublisher(
        rabbitmq_host="rabbitmq",
        rabbitmq_port=5672,
        rabbitmq_queue_name="analysis_response",
        rabbitmq_message_ttl_ms=12345,
    )

    await publisher.publish_error(
        ErrorReportPayload(
            classification="processing-error",
            reason="failed",
            path="/processing-start",
            timestamp="2026-05-17T14:00:00Z",
            correlation_id="550e8400-e29b-41d4-a716-446655440000",
        )
    )

    channel = FakeConnection.instances[0].channel_instance
    _assert_response_topology_declared(channel, ttl_ms=12345)
