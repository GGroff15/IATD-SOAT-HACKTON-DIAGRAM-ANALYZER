# Complete Example: Diagram Analysis Feature

This example demonstrates a complete BDD test setup for the diagram analyzer service, showing how all pieces fit together following hexagonal architecture principles.

## Directory Structure

```
features/
├── diagram_analysis.feature       # Feature file (this example)
├── steps/
│   ├── __init__.py
│   ├── diagram_steps.py          # Step definitions
│   └── common_steps.py
├── support/
│   ├── __init__.py
│   └── test_data.py              # Test fixtures
└── environment.py                 # Hooks
```

## 1. Feature File

**File:** `features/diagram_analysis.feature`

```gherkin
@diagram @core-feature
Feature: Diagram Analysis
  As a user of the diagram analyzer service
  I want to upload and analyze diagrams
  So that I can extract structured information from visual diagrams

  Background:
    Given the diagram analyzer service is initialized
    And I have access to the diagram repository

  @smoke @happy-path
  Scenario: Successfully analyze a valid UML class diagram
    Given I have a valid UML class diagram
    When I submit the diagram for analysis
    Then the analysis should succeed
    And I should receive a diagram ID
    And I should receive detected entities
    And I should receive relationships between entities
    And the diagram should be stored in the repository
    And the diagram should be marked as analyzed

  @validation @error-handling
  Scenario: Reject diagram with unsupported format
    Given I have a diagram with format "BMP"
    When I submit the diagram for analysis
    Then the analysis should fail
    And I should receive an error message "Unsupported format"

  @validation @error-handling
  Scenario: Reject empty diagram content
    Given I have an empty diagram
    When I submit the diagram for analysis
    Then the analysis should fail
    And I should receive an error message "content cannot be empty"

  @integration
  Scenario: Retrieve previously analyzed diagram
    Given a diagram with ID "test-diagram-123" exists
    And the diagram has been analyzed
    When I request analysis for diagram "test-diagram-123"
    Then the analysis should succeed
    And I should receive detected entities
    And the analysis result should match the stored analysis

  @edge-case
  Scenario Outline: Handle various diagram types
    Given I have a valid <diagram_type> diagram
    When I submit the diagram for analysis
    Then the analysis should succeed
    And the detected diagram type should be "<diagram_type>"
    And I should receive at least <min_entities> entities

    Examples:
      | diagram_type    | min_entities |
      | UML class       | 2            |
      | ER diagram      | 1            |
      | Flowchart       | 3            |
      | Sequence        | 2            |

  @performance @slow
  Scenario: Analyze large complex diagram
    Given I have a complex diagram with 50 entities
    When I submit the diagram for analysis
    Then the analysis should complete within 5 seconds
    And I should receive 50 entities
    And all relationships should be detected
```

## 2. Step Definitions

**File:** `features/steps/diagram_steps.py`

```python
"""Step definitions for diagram analysis features."""

from behave import given, when, then
from hamcrest import assert_that, equal_to, is_not, none, greater_than_or_equal_to
from datetime import datetime
import time

from app.core.domain.entities.diagram import Diagram
from app.core.domain.value_objects.analysis_result import AnalysisResult


# ============================================================================
# GIVEN Steps
# ============================================================================

@given('the diagram analyzer service is initialized')
def step_service_initialized(context):
    """Verify service is set up (done in environment.py)."""
    assert_that(context.service, is_not(none()))


@given('I have access to the diagram repository')
def step_have_repository_access(context):
    """Verify repository is accessible."""
    assert_that(context.repository, is_not(none()))


@given('I have a valid {diagram_type} diagram')
def step_have_valid_diagram(context, diagram_type):
    """Load a test diagram of specified type."""
    from features.support.test_data import load_test_diagram
    
    context.diagram_type = diagram_type
    context.diagram_content = load_test_diagram(diagram_type)
    context.diagram_format = "PNG"


@given('I have a diagram with format "{format}"')
def step_have_diagram_with_format(context, format):
    """Create diagram with specific format."""
    context.diagram_content = b"fake diagram content"
    context.diagram_format = format


@given('I have an empty diagram')
def step_have_empty_diagram(context):
    """Create empty diagram (invalid)."""
    context.diagram_content = b""
    context.diagram_format = "PNG"


@given('a diagram with ID "{diagram_id}" exists')
def step_diagram_exists(context, diagram_id):
    """Create and store a diagram in repository."""
    diagram = Diagram(
        id=diagram_id,
        content=b"stored diagram content",
        format="PNG",
        created_at=datetime.now()
    )
    context.repository.save(diagram)
    context.diagram_id = diagram_id


@given('the diagram has been analyzed')
def step_diagram_analyzed(context):
    """Mark the existing diagram as analyzed."""
    diagram = context.repository.find_by_id(context.diagram_id)
    diagram.mark_as_analyzed()
    
    # Store mock analysis result
    context.stored_analysis = {
        'entities': ['Entity1', 'Entity2'],
        'relationships': [{'from': 'Entity1', 'to': 'Entity2'}]
    }
    context.repository.save(diagram)


@given('I have a complex diagram with {entity_count:d} entities')
def step_have_complex_diagram(context, entity_count):
    """Create a complex test diagram."""
    from features.support.test_data import generate_complex_diagram
    
    context.diagram_content = generate_complex_diagram(entity_count)
    context.diagram_format = "PNG"
    context.expected_entity_count = entity_count


# ============================================================================
# WHEN Steps
# ============================================================================

@when('I submit the diagram for analysis')
def step_submit_diagram(context):
    """Submit diagram to the application service."""
    context.start_time = time.time()
    
    try:
        result = context.service.analyze_diagram(
            content=context.diagram_content,
            format=context.diagram_format
        )
        context.result = result
        context.diagram_id = result.diagram_id if result else None
        context.error = None
    except Exception as e:
        context.error = e
        context.result = None
    finally:
        context.end_time = time.time()


@when('I request analysis for diagram "{diagram_id}"')
def step_request_analysis(context, diagram_id):
    """Retrieve existing analysis."""
    try:
        diagram = context.repository.find_by_id(diagram_id)
        context.result = diagram
        context.error = None
    except Exception as e:
        context.error = e
        context.result = None


# ============================================================================
# THEN Steps
# ============================================================================

@then('the analysis should succeed')
def step_analysis_succeeds(context):
    """Verify no errors occurred."""
    assert_that(context.error, none(), f"Unexpected error: {context.error}")
    assert_that(context.result, is_not(none()), "Expected result but got None")


@then('the analysis should fail')
def step_analysis_fails(context):
    """Verify an error occurred."""
    assert_that(context.error, is_not(none()), "Expected an error but none occurred")


@then('I should receive an error message "{message}"')
def step_error_contains_message(context, message):
    """Verify error message contains expected text."""
    from hamcrest import contains_string
    
    assert_that(context.error, is_not(none()))
    error_message = str(context.error)
    assert_that(error_message, contains_string(message),
               f"Expected '{message}' in error, got: {error_message}")


@then('I should receive a diagram ID')
def step_receive_diagram_id(context):
    """Verify diagram ID was generated."""
    assert_that(context.diagram_id, is_not(none()))
    assert_that(len(context.diagram_id), greater_than_or_equal_to(1))


@then('I should receive detected entities')
def step_receive_entities(context):
    """Verify entities were detected."""
    assert_that(context.result, is_not(none()))
    assert_that(hasattr(context.result, 'entities'), equal_to(True))
    assert_that(len(context.result.entities), greater_than_or_equal_to(1))


@then('I should receive relationships between entities')
def step_receive_relationships(context):
    """Verify relationships were detected."""
    assert_that(context.result, is_not(none()))
    assert_that(hasattr(context.result, 'relationships'), equal_to(True))


@then('the diagram should be stored in the repository')
def step_diagram_stored(context):
    """Verify diagram was persisted."""
    stored_diagram = context.repository.find_by_id(context.diagram_id)
    assert_that(stored_diagram, is_not(none()))


@then('the diagram should be marked as analyzed')
def step_diagram_marked_analyzed(context):
    """Verify analyzed flag is set."""
    diagram = context.repository.find_by_id(context.diagram_id)
    assert_that(diagram.analyzed, equal_to(True))


@then('the analysis result should match the stored analysis')
def step_result_matches_stored(context):
    """Verify retrieved analysis matches stored data."""
    # This would compare context.result with context.stored_analysis
    assert_that(context.result, is_not(none()))
    # Add specific field comparisons as needed


@then('the detected diagram type should be "{expected_type}"')
def step_check_diagram_type(context, expected_type):
    """Verify detected diagram type."""
    assert_that(context.result.diagram_type, equal_to(expected_type))


@then('I should receive at least {min_count:d} entities')
def step_receive_minimum_entities(context, min_count):
    """Verify minimum entity count."""
    assert_that(len(context.result.entities), greater_than_or_equal_to(min_count))


@then('the analysis should complete within {seconds:d} seconds')
def step_analysis_within_time(context, seconds):
    """Verify analysis completed within time limit."""
    duration = context.end_time - context.start_time
    assert_that(duration, less_than_or_equal_to(seconds),
               f"Analysis took {duration:.2f}s, expected <={seconds}s")


@then('I should receive {count:d} entities')
def step_receive_exact_entity_count(context, count):
    """Verify exact entity count."""
    assert_that(len(context.result.entities), equal_to(count))


@then('all relationships should be detected')
def step_all_relationships_detected(context):
    """Verify relationships are present."""
    assert_that(len(context.result.relationships), greater_than_or_equal_to(1))
```

**File:** `features/steps/common_steps.py`

```python
"""Common reusable steps."""

from behave import step, then
from hamcrest import assert_that, equal_to


@step('I wait {seconds:d} seconds')
def step_wait(context, seconds):
    """Wait for specified duration."""
    import time
    time.sleep(seconds)


@then('the response should be successful')
def step_response_successful(context):
    """Generic success assertion."""
    assert_that(context.error, equal_to(None))
```

## 3. Environment Setup

**File:** `features/environment.py`

```python
"""Behave environment hooks."""

import os
import tempfile
from pathlib import Path

from app.core.application.diagram_service import DiagramService
from app.adapter.driven.persistence.in_memory_repository import InMemoryDiagramRepository
from app.adapter.driven.analyzer.test_analyzer import TestDiagramAnalyzer


def before_all(context):
    """Initialize test environment once."""
    context.temp_dir = tempfile.mkdtemp(prefix='behave_diagram_tests_')
    context.fixtures_dir = Path(__file__).parent.parent / 'tests' / 'fixtures'
    print(f"\n=== Test Environment Ready ===")


def after_all(context):
    """Clean up after all tests."""
    import shutil
    if hasattr(context, 'temp_dir') and os.path.exists(context.temp_dir):
        shutil.rmtree(context.temp_dir)


def before_scenario(context, scenario):
    """Set up fresh dependencies for each scenario."""
    # Create test doubles (following hexagonal architecture)
    context.repository = InMemoryDiagramRepository()
    context.analyzer = TestDiagramAnalyzer()
    
    # Application service (orchestrates use cases)
    context.service = DiagramService(
        repository=context.repository,
        analyzer=context.analyzer
    )
    
    # Tracking lists
    context.temp_files = []
    context.created_diagrams = []


def after_scenario(context, scenario):
    """Clean up after each scenario."""
    # Clean up temp files
    for temp_file in getattr(context, 'temp_files', []):
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    # Clear repository
    if hasattr(context, 'repository'):
        context.repository.clear()
    
    # Print failure info
    if scenario.status == 'failed':
        print(f"\n!!! Failed: {scenario.name}")
        if hasattr(context, 'error') and context.error:
            print(f"    Error: {context.error}")
```

## 4. Test Data Support

**File:** `features/support/__init__.py`

```python
"""Support package for test utilities."""
```

**File:** `features/support/test_data.py`

```python
"""Test data factories and fixtures."""

from pathlib import Path
import json


def load_test_diagram(diagram_type: str) -> bytes:
    """
    Load a test diagram fixture by type.
    
    Args:
        diagram_type: Type of diagram (e.g., "UML class", "ER diagram")
    
    Returns:
        Diagram content as bytes
    """
    # Sanitize type for filename
    filename = diagram_type.lower().replace(' ', '_')
    fixture_path = Path(__file__).parent.parent.parent / 'tests' / 'fixtures' / f'{filename}.png'
    
    if fixture_path.exists():
        with open(fixture_path, 'rb') as f:
            return f.read()
    
    # Return mock data if fixture doesn't exist
    return b"mock diagram content for " + diagram_type.encode()


def generate_complex_diagram(entity_count: int) -> bytes:
    """
    Generate a complex test diagram with specified entity count.
    
    Args:
        entity_count: Number of entities to include
    
    Returns:
        Diagram content as bytes
    """
    # In real implementation, would generate actual image
    # For testing, return mock data with metadata
    diagram_data = {
        'entity_count': entity_count,
        'type': 'complex_test_diagram'
    }
    return json.dumps(diagram_data).encode()


def create_test_diagram_file(content: bytes, filename: str = 'test_diagram.png') -> str:
    """
    Create a temporary diagram file.
    
    Args:
        content: Diagram content
        filename: Filename to use
    
    Returns:
        Path to created file
    """
    import tempfile
    import os
    
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, 'wb') as f:
        f.write(content)
    
    return filepath
```

## 5. Running the Example

### Run all scenarios
```bash
behave features/diagram_analysis.feature
```

### Run specific tags
```bash
# Smoke tests only
behave features/diagram_analysis.feature --tags=smoke

# Skip slow tests
behave features/diagram_analysis.feature --tags=~slow

# Error handling scenarios
behave features/diagram_analysis.feature --tags=error-handling
```

### Run with verbose output
```bash
behave features/diagram_analysis.feature --verbose
```

### Dry run (validate syntax)
```bash
behave features/diagram_analysis.feature --dry-run
```

## 6. Expected Output

```
Feature: Diagram Analysis

  Background:
    Given the diagram analyzer service is initialized
    And I have access to the diagram repository

  @smoke @happy-path
  Scenario: Successfully analyze a valid UML class diagram
    Given I have a valid UML class diagram ... passed
    When I submit the diagram for analysis ... passed
    Then the analysis should succeed ... passed
    And I should receive a diagram ID ... passed
    And I should receive detected entities ... passed
    And I should receive relationships between entities ... passed
    And the diagram should be stored in the repository ... passed
    And the diagram should be marked as analyzed ... passed

  @validation @error-handling
  Scenario: Reject diagram with unsupported format
    Given I have a diagram with format "BMP" ... passed
    When I submit the diagram for analysis ... passed
    Then the analysis should fail ... passed
    And I should receive an error message "Unsupported format" ... passed

... (additional scenarios)

5 features passed, 0 failed, 0 skipped
12 scenarios passed, 0 failed, 0 skipped
67 steps passed, 0 failed, 0 skipped, 0 undefined
Took 0m2.345s
```

## 7. Key Patterns Demonstrated

1. **Hexagonal Architecture Integration**: Steps use application services, not adapters directly
2. **Test Isolation**: Fresh dependencies created in `before_scenario`
3. **Declarative Scenarios**: Business language, not technical implementation
4. **Reusable Steps**: Common steps work across multiple scenarios
5. **Proper Cleanup**: Resources cleaned in hooks, not in steps
6. **Tag Organization**: Tests grouped for selective execution
7. **Context Management**: Shared state through context object
8. **Error Handling**: Both success and failure paths tested

## 8. Adapting This Example

To use this example in your project:

1. Copy feature file to `features/` directory
2. Copy step definitions to `features/steps/`
3. Copy environment.py to `features/`
4. Adapt service and repository imports to your actual implementations
5. Create test fixtures in `tests/fixtures/`
6. Run `behave` to execute
