import pytest

from app.core.domain.entities.llm_architecture_analysis import (
    LlmAnalysisErrorMetadata,
    LlmArchitectureAnalysis,
)


def test_llm_architecture_analysis_requires_summary_in_recommendations() -> None:
    with pytest.raises(ValueError, match="summary"):
        LlmArchitectureAnalysis(risks=tuple(), recommendations=tuple())


def test_llm_architecture_analysis_accepts_risks_and_recommendations() -> None:
    analysis = LlmArchitectureAnalysis(
        risks=("Unbounded synchronous fan-out in service layer",),
        recommendations=(
            "Architecture has elevated coupling risk in synchronous service paths.",
            "Prioritize async messaging for cross-domain interactions.",
        ),
    )

    assert len(analysis.risks) == 1
    assert analysis.recommendations[0].startswith("Architecture has elevated coupling risk")


def test_llm_analysis_error_metadata_validates_input() -> None:
    with pytest.raises(ValueError, match="code"):
        LlmAnalysisErrorMetadata(code="", message="timeout")
