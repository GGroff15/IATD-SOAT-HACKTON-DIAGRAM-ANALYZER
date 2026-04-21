from uuid import uuid4

from app.core.application.services.architecture_prompt_builder import (
    MistralArchitecturePromptBuilder,
)
from app.core.domain.entities.architectural_validation import (
    ArchitecturalRuleViolation,
    ArchitecturalValidationResult,
)
from app.core.domain.entities.detected_component import DetectedComponent
from app.core.domain.entities.detected_connection import ConnectionType
from app.core.domain.entities.graph import Graph, GraphEdge, GraphNode


def test_prompt_builder_generates_system_and_user_messages() -> None:
    builder = MistralArchitecturePromptBuilder()
    graph = Graph(
        diagram_upload_id=uuid4(),
        nodes=(
            GraphNode(
                node_id=0,
                component=DetectedComponent(
                    class_name="service",
                    confidence=0.9,
                    x=10.0,
                    y=10.0,
                    width=100.0,
                    height=50.0,
                    extracted_text="Orders Service",
                ),
            ),
        ),
        edges=(
            GraphEdge(
                edge_id=0,
                connection_type=ConnectionType.ARROW,
                confidence=0.8,
                start_point=(10.0, 10.0),
                end_point=(120.0, 10.0),
                source_node_id=0,
                target_node_id=0,
            ),
        ),
    )
    validation_result = ArchitecturalValidationResult(
        diagram_upload_id=graph.diagram_upload_id,
        is_valid=False,
        violations=(
            ArchitecturalRuleViolation(
                code="SELF_DEPENDENCY",
                message="Components cannot depend on themselves",
                edge_id=0,
            ),
        ),
    )

    messages = builder.build_messages(graph=graph, validation_result=validation_result)

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "As an architect or developer" in messages[0]["content"]
    assert "Assign a risk score per node" in messages[0]["content"]
    assert "first recommendations item MUST be the concise overall summary" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "SELF_DEPENDENCY" in messages[1]["content"]
    assert "Orders Service" in messages[1]["content"]
