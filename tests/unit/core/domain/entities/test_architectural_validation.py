from uuid import uuid4

import pytest

from app.core.domain.entities.architectural_validation import (
    ArchitecturalRuleViolation,
    ArchitecturalValidationResult,
    ViolationSeverity,
)


def test_violation_defaults_to_error_severity() -> None:
    violation = ArchitecturalRuleViolation(code="RULE_CODE", message="Rule failed")

    assert violation.severity == ViolationSeverity.ERROR


def test_result_is_valid_when_only_warnings_are_present() -> None:
    result = ArchitecturalValidationResult(
        diagram_upload_id=uuid4(),
        is_valid=True,
        violations=(
            ArchitecturalRuleViolation(
                code="WARN_ONLY",
                message="Warning",
                severity=ViolationSeverity.WARNING,
            ),
        ),
    )

    assert result.is_valid is True
    assert len(result.warning_violations) == 1
    assert len(result.error_violations) == 0


def test_result_rejects_valid_when_error_exists() -> None:
    with pytest.raises(ValueError, match="is_valid cannot be True when error violations are present"):
        ArchitecturalValidationResult(
            diagram_upload_id=uuid4(),
            is_valid=True,
            violations=(
                ArchitecturalRuleViolation(
                    code="ERR",
                    message="Error",
                    severity=ViolationSeverity.ERROR,
                ),
            ),
        )


def test_result_rejects_invalid_without_error_violations() -> None:
    with pytest.raises(ValueError, match="is_valid cannot be False when no error violations are present"):
        ArchitecturalValidationResult(
            diagram_upload_id=uuid4(),
            is_valid=False,
            violations=(
                ArchitecturalRuleViolation(
                    code="WARN",
                    message="Warning",
                    severity=ViolationSeverity.WARNING,
                ),
            ),
        )
