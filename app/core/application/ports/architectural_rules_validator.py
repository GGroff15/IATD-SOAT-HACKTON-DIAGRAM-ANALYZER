from typing import Protocol

from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.graph import Graph


class ArchitecturalRulesValidator(Protocol):
    """Port for validating architectural rules against a built graph."""

    def validate(self, graph: Graph) -> ArchitecturalValidationResult:
        """Validate architectural constraints on the provided graph.

        Args:
            graph: Graph generated from diagram analysis

        Returns:
            Structured validation result with rule violations when present
        """
        ...
