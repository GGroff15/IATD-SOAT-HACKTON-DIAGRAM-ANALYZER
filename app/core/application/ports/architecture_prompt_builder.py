from typing import Protocol

from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.graph import Graph


class ArchitecturePromptBuilder(Protocol):
    """Port for building LLM prompt messages for architecture analysis."""

    def build_messages(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
    ) -> tuple[dict[str, str], ...]:
        """Build chat messages containing architecture context and instructions."""
