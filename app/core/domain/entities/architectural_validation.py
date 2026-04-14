from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class ArchitecturalRuleViolation:
    """Represents a single architectural rule violation detected in a graph."""

    code: str
    message: str
    node_id: int | None = None
    edge_id: int | None = None

    def __post_init__(self) -> None:
        if not self.code or not isinstance(self.code, str):
            raise ValueError("code must be a non-empty string")
        if not self.message or not isinstance(self.message, str):
            raise ValueError("message must be a non-empty string")
        if self.node_id is not None and self.node_id < 0:
            raise ValueError("node_id must be non-negative or None")
        if self.edge_id is not None and self.edge_id < 0:
            raise ValueError("edge_id must be non-negative or None")


@dataclass(frozen=True)
class ArchitecturalValidationResult:
    """Validation output containing pass/fail and all rule violations."""

    diagram_upload_id: UUID
    is_valid: bool
    violations: tuple[ArchitecturalRuleViolation, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.diagram_upload_id, UUID):
            raise TypeError("diagram_upload_id must be a UUID")
        if not isinstance(self.is_valid, bool):
            raise TypeError("is_valid must be a bool")
        if not isinstance(self.violations, tuple):
            raise TypeError("violations must be a tuple")
        for violation in self.violations:
            if not isinstance(violation, ArchitecturalRuleViolation):
                raise TypeError("all violations must be ArchitecturalRuleViolation instances")
        if self.is_valid and self.violations:
            raise ValueError("is_valid cannot be True when violations are present")
        if not self.is_valid and not self.violations:
            raise ValueError("is_valid cannot be False when no violations are present")
