from uuid import uuid4

from app.core.application.services.architectural_rules_validator_service import (
    ArchitecturalRulesValidatorService,
)
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType
from app.core.domain.entities.graph import Graph, GraphEdge, GraphNode


def test_validator_returns_valid_when_graph_has_no_violations() -> None:
    diagram_upload_id = uuid4()
    component = DetectedComponent(
        class_name="service",
        confidence=0.9,
        x=10.0,
        y=20.0,
        width=100.0,
        height=40.0,
    )
    graph = Graph(
        diagram_upload_id=diagram_upload_id,
        nodes=(GraphNode(node_id=0, component=component),),
        edges=tuple(),
    )

    validator = ArchitecturalRulesValidatorService()

    result = validator.validate(graph)

    assert result.diagram_upload_id == diagram_upload_id
    assert result.is_valid is True
    assert result.violations == tuple()


def test_validator_returns_violation_for_empty_graph() -> None:
    graph = Graph(diagram_upload_id=uuid4(), nodes=tuple(), edges=tuple())

    validator = ArchitecturalRulesValidatorService()

    result = validator.validate(graph)

    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "GRAPH_WITHOUT_COMPONENTS"


def test_validator_returns_violation_for_self_dependency_edge() -> None:
    component = DetectedComponent(
        class_name="service",
        confidence=0.9,
        x=10.0,
        y=20.0,
        width=100.0,
        height=40.0,
    )
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(GraphNode(node_id=0, component=component),),
        edges=(
            GraphEdge(
                edge_id=0,
                connection_type=ConnectionType.ARROW,
                confidence=0.8,
                start_point=(10.0, 20.0),
                end_point=(50.0, 60.0),
                source_node_id=0,
                target_node_id=0,
            ),
        ),
    )

    validator = ArchitecturalRulesValidatorService()

    result = validator.validate(graph)

    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "SELF_DEPENDENCY"
