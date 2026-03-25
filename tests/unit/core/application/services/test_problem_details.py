from app.core.application.exceptions import ProcessingError
from app.adapter.driver.api.problem_details import (
    FALLBACK_PROBLEM_TYPE,
    map_exception_to_problem,
)


def test_map_exception_to_problem_maps_known_exception() -> None:
    problem, classification = map_exception_to_problem(
        ProcessingError("processing failed"),
        instance="/processing-start",
    )

    assert problem.status == 422
    assert problem.type == "urn:diagram-analyzer:error:processing-error"
    assert problem.title == "Processing Error"
    assert classification == "processing-error"


def test_map_exception_to_problem_uses_single_fallback_urn_for_unknown_exceptions() -> None:
    problem, classification = map_exception_to_problem(
        RuntimeError("database password=secret"),
        instance="/processing-start",
    )

    assert problem.status == 500
    assert problem.type == FALLBACK_PROBLEM_TYPE
    assert problem.detail == "An unexpected error occurred."
    assert classification == "internal"
