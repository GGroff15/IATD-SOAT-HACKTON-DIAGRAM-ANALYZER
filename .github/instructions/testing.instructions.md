---
description: Testing guidelines, structure, and when to use testing skills
applyTo: 'tests/**/*.py'
---

# Testing Guidelines

## Test Structure

Mirror `app/` structure in `tests/`:

```
tests/
├── unit/                           # Test individual functions/classes
│   ├── core/
│   │   ├── application/
│   │   └── domain/
│   └── adapter/
├── integration/                    # Test component interactions
│   └── test_diagram_workflow.py
└── e2e/                           # Test full workflows
    └── test_api_endpoints.py
```

### BDD Test Structure

Behavior tests use Behave and live in `features/`:

```
features/
├── diagram_analysis.feature       # Gherkin scenarios
├── diagram_upload.feature
├── steps/                         # Step definitions
│   ├── diagram_steps.py
│   └── common_steps.py
└── environment.py                 # Behave hooks and setup
```

## Naming Conventions

- **Test files:** `test_<module_name>.py`
- **Test functions:** `test_<function>_<scenario>()`

Examples:
- `test_diagram_service.py`
- `test_analyze_diagram_success()`
- `test_analyze_diagram_raises_error_when_format_invalid()`

## Coverage Requirements

- **Target:** 80%+ overall coverage
- **Critical paths:** 100% coverage (domain and application layers)
- **Run with:** `pytest --cov=app tests/`

## Test Type Guidelines

### Unit Tests (`tests/unit/`)

**When to use:**
- Testing individual functions or classes in isolation
- Testing domain entities and business logic
- Testing application services with mocked dependencies
- Testing adapter implementations

**Key principle:** Mock all external dependencies.

**Use the `unit-test` skill** when writing unit tests. The skill provides:
- Layer-specific patterns (domain, application, driver, driven)
- Mocking strategies for each layer
- Fixtures and common patterns
- AAA (Arrange-Act-Assert) examples

### BDD Tests (`features/`)

**When to use:**
- Describing user-facing behavior in business language
- Validating acceptance criteria with stakeholders
- Testing complete workflows from user perspective
- Creating living documentation of system behavior

**Key principle:** Write scenarios in Gherkin (Given/When/Then) that non-technical stakeholders can read.

**Use the `behavior-test` skill** when writing BDD tests. The skill provides:
- Gherkin writing guidelines and best practices
- Step definition patterns and templates
- Environment hooks setup (before/after scenarios)
- Integration with hexagonal architecture
- Complete working examples
- Tag organization strategies

**Structure:**
- **Feature files:** `.feature` files with Gherkin scenarios
- **Step definitions:** Python implementations in `features/steps/`
- **Environment hooks:** Setup/teardown in `features/environment.py`

**Example scenario:**
```gherkin
Feature: Diagram Analysis
  As a user
  I want to upload and analyze diagrams
  So that I can extract structured information

  Scenario: Analyze valid UML diagram
    Given I have a valid UML class diagram
    When I upload the diagram for analysis
    Then the analysis should succeed
    And I should receive detected entities
    And I should receive relationships between entities
```

### Integration Tests (`tests/integration/`)

**When to use:**
- Testing workflows across multiple layers
- Testing adapter implementations with real resources (temp files, in-memory data)
- Validating that ports and adapters integrate correctly
- Testing transaction boundaries

**Key principle:** Use real implementations where practical with temporary resources.

**Use the `integration-test` skill** when writing integration tests. The skill provides:
- Multi-layer workflow patterns
- Real vs mock component decisions
- Temporary resource management
- Transaction and state testing

### E2E Tests (`tests/e2e/`)

**When to use:**
- Testing complete user workflows
- Testing with external dependencies (LocalStack for AWS)

**Key principle:** Test the full system as users would interact with it.

## Test Fixtures

Create shared fixtures in `tests/conftest.py` for common test setup. Layer-specific fixtures go in their respective `conftest.py` files:
- `tests/unit/conftest.py` - Unit test fixtures
- `tests/integration/conftest.py` - Integration test fixtures

## When to Use Which Skill

| Task | Skill | Why |
|------|-------|-----|
| Writing tests for domain entities | `unit-test` | Pure logic, no dependencies |
| Writing tests for application services | `unit-test` | Mock all adapters |
| Writing tests for repositories | `unit-test` or `integration-test` | Unit for mocked I/O, integration for temp resources |
| Testing full workflow (upload → analyze) | `integration-test` | Multiple layers involved |
| Testing event listener → service → persistence | `integration-test` | End-to-end component flow |
| Validating acceptance criteria in business language | `behavior-test` | Stakeholder-readable Gherkin scenarios |
| Writing Given/When/Then scenarios | `behavior-test` | BDD with Behave framework |
| Creating living documentation | `behavior-test` | Feature files as documentation |

## Running Tests

### Pytest (Unit/Integration/E2E)

```bash
# All tests
pytest

# Specific type
pytest tests/unit/
pytest tests/integration/

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/unit/core/application/test_diagram_service.py
```

### Behave (BDD)

```bash
# All feature files
behave

# Specific feature
behave features/diagram_analysis.feature

# Specific scenario by tag
behave --tags=@smoke

# With verbose output
behave --verbose

# Dry run (check syntax)
behave --dry-run
```
