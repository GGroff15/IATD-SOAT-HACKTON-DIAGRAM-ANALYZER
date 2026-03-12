from typing import Protocol

from app.core.domain.entities.diagram_analysis_result import DiagramAnalysisResult
from app.core.domain.entities.graph import Graph


class GraphBuilder(Protocol):
    """Port for building graphs from diagram analysis results."""

    def build(self, analysis_result: DiagramAnalysisResult) -> Graph:
        """Build a graph from the analysis result.

        Args:
            analysis_result: Diagram analysis result with components and connections

        Returns:
            Graph containing nodes and edges derived from the analysis
        """
        ...
