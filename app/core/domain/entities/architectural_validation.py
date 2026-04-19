from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


class ViolationSeverity(Enum):
    """Severity levels for architectural findings."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ArchitecturalRuleViolation:
    """Represents a single architectural rule violation detected in a graph."""

    code: str
    message: str
    node_id: int | None = None
    edge_id: int | None = None
    severity: ViolationSeverity = ViolationSeverity.ERROR

    def __post_init__(self) -> None:
        if not self.code or not isinstance(self.code, str):
            raise ValueError("code must be a non-empty string")
        if not self.message or not isinstance(self.message, str):
            raise ValueError("message must be a non-empty string")
        if self.node_id is not None and self.node_id < 0:
            raise ValueError("node_id must be non-negative or None")
        if self.edge_id is not None and self.edge_id < 0:
            raise ValueError("edge_id must be non-negative or None")
        if not isinstance(self.severity, ViolationSeverity):
            raise TypeError("severity must be a ViolationSeverity")


@dataclass(frozen=True)
class ArchitecturalValidationResult:
    """Validation output containing pass/fail and all rule violations."""

    diagram_upload_id: UUID
    is_valid: bool
    violations: tuple[ArchitecturalRuleViolation, ...] = field(default_factory=tuple)

    @property
    def error_violations(self) -> tuple[ArchitecturalRuleViolation, ...]:
        """Return only error-level violations."""
        return tuple(
            violation
            for violation in self.violations
            if violation.severity == ViolationSeverity.ERROR
        )

    @property
    def warning_violations(self) -> tuple[ArchitecturalRuleViolation, ...]:
        """Return only warning-level findings."""
        return tuple(
            violation
            for violation in self.violations
            if violation.severity == ViolationSeverity.WARNING
        )

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

        has_error_violations = any(
            violation.severity == ViolationSeverity.ERROR
            for violation in self.violations
        )
        if self.is_valid and has_error_violations:
            raise ValueError("is_valid cannot be True when error violations are present")
        if not self.is_valid and not has_error_violations:
            raise ValueError("is_valid cannot be False when no error violations are present")
