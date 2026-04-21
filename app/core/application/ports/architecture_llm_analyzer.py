from typing import Protocol

from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.graph import Graph
from app.core.domain.entities.llm_architecture_analysis import LlmArchitectureAnalysis


class ArchitectureLlmAnalyzer(Protocol):
    """Port for generating architecture risk/recommendation analysis with an LLM."""

    async def analyze(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
    ) -> LlmArchitectureAnalysis:
        """Analyze graph + rule violations and return structured findings."""
