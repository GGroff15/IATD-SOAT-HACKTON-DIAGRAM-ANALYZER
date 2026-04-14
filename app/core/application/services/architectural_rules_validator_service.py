from app.core.domain.entities.architectural_validation import (
    ArchitecturalRuleViolation,
    ArchitecturalValidationResult,
)
from app.core.domain.entities.graph import Graph


class ArchitecturalRulesValidatorService:
    """Applies baseline architectural validation rules to a diagram graph."""

    def validate(self, graph: Graph) -> ArchitecturalValidationResult:
        """Validate architectural rules and return all violations.

        Baseline rules:
        - Graph must contain at least one component node
        - Edges cannot represent self-dependency (source == target)
        """
        violations: list[ArchitecturalRuleViolation] = []

        if graph.node_count == 0:
            violations.append(
                ArchitecturalRuleViolation(
                    code="GRAPH_WITHOUT_COMPONENTS",
                    message="Graph must include at least one component node",
                )
            )

        for edge in graph.edges:
            if edge.source_node_id is not None and edge.source_node_id == edge.target_node_id:
                violations.append(
                    ArchitecturalRuleViolation(
                        code="SELF_DEPENDENCY",
                        message="Components cannot depend on themselves",
                        edge_id=edge.edge_id,
                    )
                )

        return ArchitecturalValidationResult(
            diagram_upload_id=graph.diagram_upload_id,
            is_valid=len(violations) == 0,
            violations=tuple(violations),
        )
