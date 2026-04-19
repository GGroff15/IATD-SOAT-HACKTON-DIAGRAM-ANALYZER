from uuid import uuid4

from app.core.application.services.architectural_rules_validator_service import (
    ArchitecturalRulesValidatorService,
)
from app.core.domain.entities.architectural_validation import ViolationSeverity
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType
from app.core.domain.entities.graph import Graph, GraphEdge, GraphNode


def _node(node_id: int, class_name: str, text: str | None = None) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        component=DetectedComponent(
            class_name=class_name,
            confidence=0.9,
            x=float(node_id * 10),
            y=float(node_id * 5),
            width=100.0,
            height=40.0,
            extracted_text=text,
        ),
    )


def _edge(
    edge_id: int,
    source: int,
    target: int,
    connection_type: ConnectionType = ConnectionType.ARROW,
) -> GraphEdge:
    return GraphEdge(
        edge_id=edge_id,
        connection_type=connection_type,
        confidence=0.8,
        start_point=(10.0 + edge_id, 20.0 + edge_id),
        end_point=(50.0 + edge_id, 60.0 + edge_id),
        source_node_id=source,
        target_node_id=target,
    )


def test_validator_returns_valid_for_downstream_and_async_flow() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(
            _node(0, "actor", "User"),
            _node(1, "gateway", "API Gateway"),
            _node(2, "service", "Orders Service"),
            _node(3, "database", "Orders DB"),
            _node(4, "queue", "Orders Queue"),
            _node(5, "service", "Billing Service"),
        ),
        edges=(
            _edge(0, 0, 1),
            _edge(1, 1, 2),
            _edge(2, 2, 3),
            _edge(3, 2, 4),
            _edge(4, 4, 5, connection_type=ConnectionType.DASHED),
        ),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is True
    assert result.violations == tuple()


def test_validator_returns_violation_for_empty_graph() -> None:
    graph = Graph(diagram_upload_id=uuid4(), nodes=tuple(), edges=tuple())

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is False
    assert any(violation.code == "GRAPH_WITHOUT_COMPONENTS" for violation in result.violations)


def test_validator_returns_violation_for_self_dependency_edge() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(_node(0, "service"),),
        edges=(_edge(0, 0, 0),),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is False
    assert any(violation.code == "SELF_DEPENDENCY" for violation in result.violations)


def test_validator_rejects_forbidden_user_to_database_connection() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(_node(0, "user"), _node(1, "database")),
        edges=(_edge(0, 0, 1),),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is False
    assert any(violation.code == "FORBIDDEN_CONNECTION" for violation in result.violations)


def test_validator_requires_at_least_one_gateway_and_service() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(_node(0, "database"), _node(1, "queue")),
        edges=(_edge(0, 1, 0),),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    codes = {violation.code for violation in result.violations}
    assert "MISSING_API_GATEWAY" in codes
    assert "MISSING_SERVICE" in codes


def test_validator_rejects_isolated_nodes() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(_node(0, "user"), _node(1, "gateway"), _node(2, "service")),
        edges=(_edge(0, 0, 1),),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is False
    assert any(violation.code == "ISOLATED_NODE" and violation.node_id == 2 for violation in result.violations)


def test_validator_rejects_database_outbound_dependencies() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(_node(0, "database"), _node(1, "service")),
        edges=(_edge(0, 0, 1),),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is False
    assert any(violation.code == "DATABASE_MUST_BE_SINK" for violation in result.violations)


def test_validator_rejects_queue_not_between_services() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(_node(0, "user"), _node(1, "queue"), _node(2, "service")),
        edges=(_edge(0, 0, 1), _edge(1, 1, 2)),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is False
    assert any(violation.code == "QUEUE_MUST_CONNECT_SERVICES" for violation in result.violations)


def test_validator_warns_for_queue_without_consumer() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(
            _node(0, "user"),
            _node(1, "api_gateway"),
            _node(2, "service"),
            _node(3, "queue"),
        ),
        edges=(_edge(0, 0, 1), _edge(1, 1, 2), _edge(2, 2, 3)),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is True
    assert any(
        violation.code == "QUEUE_WITHOUT_CONSUMER"
        and violation.severity == ViolationSeverity.WARNING
        for violation in result.violations
    )


def test_validator_warns_when_service_has_excessive_fan_out() -> None:
    validator = ArchitecturalRulesValidatorService(service_fan_out_warning_threshold=1)
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(
            _node(0, "user"),
            _node(1, "gateway"),
            _node(2, "service"),
            _node(3, "service"),
            _node(4, "service"),
        ),
        edges=(
            _edge(0, 0, 1),
            _edge(1, 1, 2),
            _edge(2, 2, 3),
            _edge(3, 2, 4),
        ),
    )

    result = validator.validate(graph)

    assert result.is_valid is True
    assert any(
        violation.code == "GOD_SERVICE_FAN_OUT"
        and violation.severity == ViolationSeverity.WARNING
        for violation in result.violations
    )


def test_validator_warns_when_database_has_excessive_fan_in() -> None:
    validator = ArchitecturalRulesValidatorService(database_fan_in_warning_threshold=1)
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(
            _node(0, "user"),
            _node(1, "gateway"),
            _node(2, "service"),
            _node(3, "service"),
            _node(4, "database"),
        ),
        edges=(
            _edge(0, 0, 1),
            _edge(1, 1, 2),
            _edge(2, 2, 4),
            _edge(3, 3, 4),
        ),
    )

    result = validator.validate(graph)

    assert result.is_valid is True
    assert any(
        violation.code == "DATABASE_TIGHT_COUPLING"
        and violation.severity == ViolationSeverity.WARNING
        for violation in result.violations
    )


def test_validator_rejects_bidirectional_sync_dependencies() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(_node(0, "service"), _node(1, "service"), _node(2, "gateway")),
        edges=(_edge(0, 2, 0), _edge(1, 0, 1), _edge(2, 1, 0)),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is False
    assert any(violation.code == "BIDIRECTIONAL_DEPENDENCY" for violation in result.violations)


def test_validator_rejects_sync_cycle() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(
            _node(0, "user"),
            _node(1, "gateway"),
            _node(2, "service"),
            _node(3, "service"),
            _node(4, "service"),
        ),
        edges=(
            _edge(0, 0, 1),
            _edge(1, 1, 2),
            _edge(2, 2, 3),
            _edge(3, 3, 4),
            _edge(4, 4, 2),
        ),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is False
    assert any(
        violation.code == "SYNC_CYCLE_DETECTED"
        and violation.severity == ViolationSeverity.ERROR
        for violation in result.violations
    )


def test_validator_warns_for_async_cycle() -> None:
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(_node(0, "service"), _node(1, "queue"), _node(2, "service"), _node(3, "gateway")),
        edges=(
            _edge(0, 3, 0),
            _edge(1, 0, 1, connection_type=ConnectionType.DASHED),
            _edge(2, 1, 2, connection_type=ConnectionType.DASHED),
            _edge(3, 2, 0, connection_type=ConnectionType.DASHED),
        ),
    )

    result = ArchitecturalRulesValidatorService().validate(graph)

    assert result.is_valid is True
    assert any(
        violation.code == "ASYNC_CYCLE_DETECTED"
        and violation.severity == ViolationSeverity.WARNING
        for violation in result.violations
    )
