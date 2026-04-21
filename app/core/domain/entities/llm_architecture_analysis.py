from dataclasses import dataclass, field


@dataclass(frozen=True)
class LlmArchitectureAnalysis:
    """Structured LLM analysis containing risks and recommendations."""

    risks: tuple[str, ...] = field(default_factory=tuple)
    recommendations: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.risks, tuple):
            raise TypeError("risks must be a tuple")
        if not isinstance(self.recommendations, tuple):
            raise TypeError("recommendations must be a tuple")
        if len(self.recommendations) == 0:
            raise ValueError("recommendations must include summary as the first item")

        for risk in self.risks:
            if not isinstance(risk, str) or not risk.strip():
                raise ValueError("all risks must be non-empty strings")
        for recommendation in self.recommendations:
            if not isinstance(recommendation, str) or not recommendation.strip():
                raise ValueError("all recommendations must be non-empty strings")


@dataclass(frozen=True)
class LlmAnalysisErrorMetadata:
    """Error metadata produced when LLM analysis fails."""

    code: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("code must be a non-empty string")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string")
