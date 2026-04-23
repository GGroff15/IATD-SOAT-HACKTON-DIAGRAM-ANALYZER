from typing import Protocol

from app.core.domain.entities.architectural_validation import ArchitecturalValidationResult
from app.core.domain.entities.graph import Graph
from app.core.domain.entities.llm_architecture_analysis import (
    LlmArchitectureAnalysis,
)


class GraphResultPublisher(Protocol):
    async def publish_graph(
        self,
        graph: Graph,
        validation_result: ArchitecturalValidationResult,
        llm_analysis: LlmArchitectureAnalysis | None,
    ) -> None:
        """Publish or persist graph, validation, and optional LLM analysis metadata."""
