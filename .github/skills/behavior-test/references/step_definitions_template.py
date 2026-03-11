# Step Definitions Template for Diagram Analyzer Service
# Place this in: features/steps/

from behave import given, when, then, step
from hamcrest import (
    assert_that, equal_to, is_not, none, 
    contains_string, greater_than
)
import json
from datetime import datetime

# ============================================================================
# GIVEN Steps (Preconditions / Context Setup)
# ============================================================================

@given('I have a valid {diagram_type} diagram')
def step_have_valid_diagram(context, diagram_type):
    """
    Load a test diagram fixture.
    
    Args:
        diagram_type: Type of diagram (e.g., "UML", "ER", "flowchart")
    
    Sets context:
        - context.diagram_type
        - context.diagram_content (bytes)
        - context.diagram_format
    """
    context.diagram_type = diagram_type
    # Load from test fixtures directory
    fixture_path = f"tests/fixtures/{diagram_type.lower()}_sample.png"
    with open(fixture_path, 'rb') as f:
        context.diagram_content = f.read()
    context.diagram_format = "PNG"


@given('I have an invalid diagram with format "{format}"')
def step_have_invalid_diagram(context, format):
    """Set up an invalid diagram test case."""
    context.diagram_content = b"invalid content"
    context.diagram_format = format


@given('the diagram repository contains {count:d} diagrams')
def step_repository_has_diagrams(context, count):
    """Pre-populate repository with test diagrams."""
    from app.core.domain.entities.diagram import Diagram
    
    for i in range(count):
        diagram = Diagram(
            id=f"test-diagram-{i}",
            content=b"test content",
            format="PNG",
            created_at=datetime.now()
        )
        context.repository.save(diagram)


@given('a diagram with ID "{diagram_id}" exists')
def step_diagram_exists(context, diagram_id):
    """Create a specific diagram in the repository."""
    from app.core.domain.entities.diagram import Diagram
    
    diagram = Diagram(
        id=diagram_id,
        content=b"test diagram content",
        format="PNG",
        created_at=datetime.now()
    )
    context.repository.save(diagram)
    context.diagram_id = diagram_id


# ============================================================================
# WHEN Steps (Actions / Events)
# ============================================================================

@when('I submit the diagram for analysis')
def step_submit_diagram(context):
    """
    Submit diagram through application service.
    
    Expects context:
        - context.diagram_content
        - context.diagram_format
    
    Sets context:
        - context.result (AnalysisResult or exception)
        - context.diagram_id
    """
    try:
        result = context.service.analyze_diagram(
            content=context.diagram_content,
            format=context.diagram_format
        )
        context.result = result
        context.diagram_id = result.diagram_id
        context.error = None
    except Exception as e:
        context.error = e
        context.result = None


@when('I upload a diagram file')
def step_upload_diagram(context):
    """Upload diagram via HTTP API."""
    files = {'file': ('diagram.png', context.diagram_content, 'image/png')}
    response = context.test_client.post('/diagrams/upload', files=files)
    context.response = response
    context.status_code = response.status_code


@when('I request analysis for diagram "{diagram_id}"')
def step_request_analysis(context, diagram_id):
    """Request analysis for an existing diagram."""
    try:
        result = context.service.get_analysis(diagram_id)
        context.result = result
        context.error = None
    except Exception as e:
        context.error = e
        context.result = None


@when('I retrieve diagrams from the repository')
def step_retrieve_diagrams(context):
    """Retrieve list of diagrams."""
    context.diagrams = context.repository.find_all()


# ============================================================================
# THEN Steps (Assertions / Expected Outcomes)
# ============================================================================

@then('the analysis should succeed')
def step_analysis_succeeds(context):
    """Verify successful analysis with no errors."""
    assert_that(context.error, none(), "Expected no errors")
    assert_that(context.result, is_not(none()), "Expected analysis result")


@then('the analysis should fail')
def step_analysis_fails(context):
    """Verify analysis failed with an error."""
    assert_that(context.error, is_not(none()), "Expected an error")


@then('I should receive an error message "{message}"')
def step_error_message(context, message):
    """Verify specific error message."""
    assert_that(context.error, is_not(none()))
    assert_that(str(context.error), contains_string(message))


@then('I should receive a diagram ID')
def step_receive_diagram_id(context):
    """Verify diagram ID was returned."""
    assert_that(context.result, is_not(none()))
    assert_that(context.diagram_id, is_not(none()))
    assert_that(len(context.diagram_id), greater_than(0))


@then('I should receive detected entities')
def step_receive_entities(context):
    """Verify entities were detected in analysis."""
    assert_that(context.result, is_not(none()))
    assert_that(context.result.entities, is_not(none()))
    assert_that(len(context.result.entities), greater_than(0))


@then('I should receive relationships between entities')
def step_receive_relationships(context):
    """Verify relationships were detected."""
    assert_that(context.result.relationships, is_not(none()))


@then('the response status should be {status_code:d}')
def step_check_status_code(context, status_code):
    """Verify HTTP response status code."""
    assert_that(context.status_code, equal_to(status_code))


@then('the diagram should be marked as analyzed')
def step_diagram_marked_analyzed(context):
    """Verify diagram has analyzed status."""
    diagram = context.repository.find_by_id(context.diagram_id)
    assert_that(diagram.analyzed, equal_to(True))


@then('the diagram should be stored in the repository')
def step_diagram_stored(context):
    """Verify diagram was persisted."""
    diagram = context.repository.find_by_id(context.diagram_id)
    assert_that(diagram, is_not(none()))


@then('I should receive {count:d} diagrams')
def step_receive_count_diagrams(context, count):
    """Verify count of diagrams returned."""
    assert_that(len(context.diagrams), equal_to(count))


# ============================================================================
# Table Data Steps
# ============================================================================

@then('the analysis result should contain')
def step_analysis_contains(context):
    """
    Verify analysis result contains specific data.
    
    Example:
        Then the analysis result should contain
          | field         | value          |
          | diagram_type  | UML Class      |
          | entity_count  | 5              |
          | status        | completed      |
    """
    for row in context.table:
        field = row['field']
        expected_value = row['value']
        actual_value = getattr(context.result, field, None)
        
        # Try numeric conversion
        try:
            expected_value = int(expected_value)
        except ValueError:
            pass
        
        assert_that(actual_value, equal_to(expected_value),
                   f"Field '{field}' mismatch")


# ============================================================================
# Reusable Step Combinators
# ============================================================================

@step('I wait {seconds:d} seconds')
def step_wait(context, seconds):
    """Wait for async operations (use sparingly)."""
    import time
    time.sleep(seconds)


@step('debug context')
def step_debug(context):
    """Print context for debugging (remove in production tests)."""
    print("\n=== Context Debug ===")
    for key, value in context.__dict__.items():
        if not key.startswith('_'):
            print(f"{key}: {value}")
    print("====================\n")


# ============================================================================
# Pattern: Parameterized Step with Type Conversion
# ============================================================================

@given('the configuration parameter "{param}" is set to "{value}"')
def step_set_config(context, param, value):
    """
    Set configuration parameter with automatic type conversion.
    
    Handles: integers, floats, booleans, strings, JSON
    """
    # Try conversions
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif value.isdigit():
        value = int(value)
    elif value.replace('.', '', 1).isdigit():
        value = float(value)
    elif value.startswith('{') or value.startswith('['):
        value = json.loads(value)
    
    context.config[param] = value


# ============================================================================
# Pattern: Async Step with Context Manager
# ============================================================================

@when('I perform async analysis')
async def step_async_analysis(context):
    """
    Example of async step (requires behave-async or similar).
    
    Note: Standard Behave doesn't support async natively.
    """
    result = await context.service.analyze_diagram_async(
        context.diagram_content
    )
    context.result = result


# ============================================================================
# Helper Functions (not steps)
# ============================================================================

def load_test_diagram(diagram_type: str) -> bytes:
    """Load diagram fixture from file."""
    import os
    fixture_path = os.path.join(
        "tests", "fixtures", f"{diagram_type.lower()}_sample.png"
    )
    with open(fixture_path, 'rb') as f:
        return f.read()


def create_test_diagram(diagram_id: str | None = None):
    """Factory for creating test diagram entities."""
    from app.core.domain.entities.diagram import Diagram
    
    return Diagram(
        id=diagram_id or f"test-{datetime.now().timestamp()}",
        content=b"test content",
        format="PNG",
        created_at=datetime.now()
    )
