---
name: behavior-test
description: 'Write BDD tests using Behave for the diagram analyzer service. Use when creating Gherkin scenarios, step definitions, validating acceptance criteria, writing stakeholder-readable tests, or testing complete user workflows in business language.'
argument-hint: 'Specify: feature, steps, or hooks'
---

# Behavior Testing with Behave

Write BDD (Behavior-Driven Development) tests using Gherkin syntax and Behave for stakeholder-readable acceptance tests.

## When to Use This Skill

- Describing user-facing behavior in business language
- Validating acceptance criteria with stakeholders
- Testing complete workflows from the user's perspective
- Creating living documentation of system behavior
- Collaborating with non-technical team members on test scenarios
- Testing end-to-end flows with natural language readability

## When NOT to Use

- Testing internal implementation details → Use `unit-test`
- Testing component integration without business scenarios → Use `integration-test`
- Fast feedback during development → Use `unit-test` or `integration-test`
- Testing a single function or class → Use `unit-test`

## BDD Test Structure

```
features/
├── diagram_analysis.feature       # Gherkin scenarios
├── diagram_upload.feature
├── steps/                         # Step definitions (Python)
│   ├── __init__.py
│   ├── diagram_steps.py          # Domain-specific steps
│   ├── common_steps.py           # Reusable steps
│   └── api_steps.py
├── support/                       # Helper modules
│   ├── __init__.py
│   └── test_helpers.py
└── environment.py                 # Behave hooks (setup/teardown)
```

## Writing Gherkin Features

### Feature File Template

```gherkin
Feature: [Feature name in business language]
  [1-3 line description of business value]
  
  Background: [Optional: Common setup for all scenarios]
    Given [precondition that applies to all scenarios]
  
  Scenario: [Specific behavior description]
    Given [context/precondition]
    When [action/event]
    Then [expected outcome]
    And [additional expectations]
  
  Scenario Outline: [Parameterized scenario]
    Given <parameter> exists
    When I perform action with <parameter>
    Then I should see <result>
    
    Examples:
      | parameter | result  |
      | value1    | output1 |
      | value2    | output2 |
```

### Gherkin Best Practices

**DO:**
- ✓ Write from user/system perspective (not implementation)
- ✓ Use business domain language (ubiquitous language)
- ✓ Keep scenarios focused on ONE behavior
- ✓ Use declarative style (WHAT, not HOW)
- ✓ Make steps reusable across scenarios

**DON'T:**
- ✗ Include technical implementation details
- ✗ Test multiple behaviors in one scenario
- ✗ Use imperative UI steps ("click button", "fill field")
- ✗ Make scenarios too long (>10 steps)
- ✗ Duplicate logic across step definitions

### Example: Good vs Bad Scenarios

**❌ Bad (Imperative, UI-focused):**
```gherkin
Scenario: Upload diagram
  Given I am on the upload page
  When I click the "Choose File" button
  And I select "diagram.png" from my computer
  And I click the "Upload" button
  Then I should see "Upload successful" message
```

**✅ Good (Declarative, business-focused):**
```gherkin
Scenario: Successfully upload valid diagram
  Given I have a valid UML class diagram
  When I submit the diagram for analysis
  Then the system should accept the diagram
  And the diagram should be queued for processing
```

## Writing Step Definitions

### Step Definition Template

See [step definitions template](./references/step_definitions_template.py) for complete examples.

```python
# features/steps/diagram_steps.py
from behave import given, when, then
from hamcrest import assert_that, equal_to, is_not, none

@given('I have a valid {diagram_type} diagram')
def step_have_valid_diagram(context, diagram_type):
    """Load test fixture for diagram type."""
    context.diagram_type = diagram_type
    context.diagram_content = load_test_diagram(diagram_type)
    context.diagram_format = "PNG"

@when('I submit the diagram for analysis')
def step_submit_diagram(context):
    """Submit diagram through the application service."""
    # Use real application service (not mocked)
    service = get_diagram_service()
    context.result = service.analyze_diagram(
        content=context.diagram_content,
        format=context.diagram_format
    )

@then('the system should accept the diagram')
def step_system_accepts_diagram(context):
    """Verify successful acceptance."""
    assert_that(context.result.status, equal_to("accepted"))
    assert_that(context.result.diagram_id, is_not(none()))
```

### Step Organization Patterns

**1. Domain-Specific Steps (`diagram_steps.py`, `analysis_steps.py`)**
- Steps specific to one feature area
- Business domain language
- Strong coupling to feature files

**2. Common/Reusable Steps (`common_steps.py`)**
- Generic assertions (status codes, error messages)
- Common setup/teardown
- Weak coupling, high reusability

**3. Technical Steps (`api_steps.py`, `database_steps.py`)**
- Infrastructure-related steps
- HTTP requests, database queries
- Used across multiple features

### Context Object Best Practices

The `context` object shares state between steps:

```python
# Store test data
context.diagram = {...}
context.result = response
context.error = exception

# Store test fixtures
context.test_client = app.test_client()
context.service = DiagramService(...)

# Store temporary resources
context.temp_files = []
context.test_ids = []
```

**Guidelines:**
- Use descriptive attribute names
- Clean up in hooks, not in steps
- Don't share mutable objects without copying
- Document expected attributes in `environment.py`

## Environment Hooks

### environment.py Template

See [environment template](./references/environment_template.py) for complete example.

```python
# features/environment.py
from app.core.application import DiagramService
from app.adapter.driven.persistence import InMemoryDiagramRepository

def before_all(context):
    """Run once before all features."""
    # Initialize test configuration
    context.config = load_test_config()

def before_feature(context, feature):
    """Run before each feature file."""
    pass

def before_scenario(context, scenario):
    """Run before each scenario."""
    # Set up fresh dependencies for each scenario
    context.repository = InMemoryDiagramRepository()
    context.service = DiagramService(context.repository)
    context.temp_files = []

def after_scenario(context, scenario):
    """Run after each scenario."""
    # Clean up temporary resources
    cleanup_temp_files(context.temp_files)
    context.repository.clear()

def after_feature(context, feature):
    """Run after each feature file."""
    pass

def after_all(context):
    """Run once after all features."""
    pass
```

### Hook Execution Order

```
before_all
  before_feature
    before_scenario
      before_step
        [step execution]
      after_step
    after_scenario
  after_feature
after_all
```

## Integration with Hexagonal Architecture

### Principle: Test Through Application Layer

BDD tests should interact with the **application layer** (ports), not adapters directly:

```python
# ✅ Good: Use application service
@when('I analyze the diagram')
def step_analyze_diagram(context):
    service = DiagramService(
        repository=InMemoryDiagramRepository(),
        analyzer=TestAnalyzer()
    )
    context.result = service.analyze_diagram(
        context.diagram_content
    )

# ❌ Bad: Interact with adapter directly
@when('I analyze the diagram')
def step_analyze_diagram(context):
    repository = InMemoryDiagramRepository()
    repository.save(context.diagram)  # Bypasses business logic
```

### Use Test Doubles for Driven Adapters

Replace external dependencies with in-memory or fake implementations:

```python
# Production: Real AWS S3 client
class S3DiagramRepository:
    def __init__(self, s3_client):
        self.s3_client = s3_client

# BDD tests: In-memory implementation
class InMemoryDiagramRepository:
    def __init__(self):
        self.diagrams = {}
    
    def save(self, diagram):
        self.diagrams[diagram.id] = diagram
```

### Use Tags for Test Organization

```gherkin
@smoke @diagram
Feature: Diagram Upload
  
  @happy-path
  Scenario: Upload valid diagram
    ...
  
  @error-handling @validation
  Scenario: Reject invalid format
    ...
```

Run specific tests:
```bash
behave --tags=smoke
behave --tags=diagram --tags=~wip
behave --tags="smoke or critical"
```

## Running Behavior Tests

### Basic Commands

```bash
# Run all features
behave

# Run specific feature
behave features/diagram_analysis.feature

# Run with tags
behave --tags=smoke

# Verbose output
behave --verbose

# Dry run (validate syntax)
behave --dry-run

# Stop on first failure
behave --stop

# Format output
behave --format=pretty
behave --format=json -o report.json
```

### Common Options

```bash
# Show step definitions
behave --steps

# Show snippets for undefined steps
behave --snippets

# Use specific configuration
behave --define CONFIG=test

# Parallel execution (with behave-parallel)
behave --processes 4
```

## Workflow: Adding a New Feature

### Step-by-Step Process

**1. Write the Feature File**
- Start with business requirements
- Write scenarios from user perspective
- Use domain language
- Add tags for organization

**2. Run to Generate Step Stubs**
```bash
behave features/new_feature.feature --snippets
```

Behave will show undefined steps:
```python
@given('I have a valid diagram')
def step_impl(context):
    raise NotImplementedError
```

**3. Implement Step Definitions**
- Copy stubs to appropriate step file
- Implement using application services
- Add assertions with hamcrest

**4. Add Environment Hooks (if needed)**
- Set up test fixtures in `before_scenario`
- Clean up resources in `after_scenario`

**5. Run and Iterate**
```bash
behave features/new_feature.feature
```

**6. Verify Coverage**
- Ensure critical paths are tested
- Add negative test scenarios (error cases)
- Validate edge cases

## Example: Complete Feature Implementation

See [complete example](./examples/diagram_analysis_example.md) for a full working feature with all components.

## Tips and Troubleshooting

### Common Issues

**Problem:** Step definitions not found
- **Solution:** Ensure step files are in `features/steps/` directory
- **Solution:** Add `__init__.py` to `features/steps/`
- **Solution:** Check step pattern matches exactly (regex)

**Problem:** Context attributes not available
- **Solution:** Ensure previous steps set the attribute
- **Solution:** Initialize in `before_scenario` hook
- **Solution:** Check step execution order

**Problem:** Tests are slow
- **Solution:** Use in-memory adapters, not real external services
- **Solution:** Minimize database operations
- **Solution:** Use `@wip` tag for work-in-progress features

**Problem:** Steps are too granular/too many steps
- **Solution:** Combine technical steps into one business step
- **Solution:** Use Background for common setup
- **Solution:** Refactor imperative steps to declarative

### Best Practices Summary

1. **One scenario = One behavior**
2. **Use application layer, not adapters**
3. **Clean up in hooks, not in steps**
4. **Make steps reusable and composable**
5. **Use tags for test organization**
6. **Keep features readable by non-technical stakeholders**
7. **Use in-memory test doubles for external dependencies**
8. **Parallelize BDD vs unit/integration tests appropriately**

## Further Reading

- [Behave Documentation](https://behave.readthedocs.io/)
- [Gherkin Reference](https://cucumber.io/docs/gherkin/reference/)
- [Writing Better Gherkin](https://cucumber.io/docs/bdd/better-gherkin/)
- [Hexagonal Architecture Testing](https://herbertograca.com/2017/09/21/ports-adapters-architecture/)
