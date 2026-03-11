# Getting Started with Behavior Testing

Quick start guide for adding BDD tests to the diagram analyzer service.

## Prerequisites

Behave is already installed in your project:
```bash
uv add --dev behave
```

## Quick Start (5 Minutes)

### 1. Create Directory Structure

```bash
mkdir -p features/steps features/support
touch features/steps/__init__.py
touch features/support/__init__.py
```

### 2. Copy Environment Template

Copy from [environment_template.py](../references/environment_template.py) to `features/environment.py`:

```bash
# On Windows PowerShell
Copy-Item .github\skills\behavior-test\references\environment_template.py features\environment.py
```

### 3. Create Your First Feature

Create `features/hello.feature`:

```gherkin
Feature: Hello Behave
  Quick test to verify Behave is working

  Scenario: First test
    Given Behave is working
    When I run this test
    Then I should see success
```

### 4. Create Step Definitions

Create step file `features/steps/hello_steps.py`:

```python
from behave import given, when, then

@given('Behave is working')
def step_impl(context):
    context.behave_works = True

@when('I run this test')
def step_impl(context):
    context.test_ran = True

@then('I should see success')
def step_impl(context):
    assert context.behave_works
    assert context.test_ran
```

### 5. Run!

```bash
behave
```

You should see:
```
Feature: Hello Behave
  Scenario: First test
    Given Behave is working ... passed
    When I run this test ... passed
    Then I should see success ... passed

1 feature passed, 0 failed, 0 skipped
1 scenario passed, 0 failed, 0 skipped
3 steps passed, 0 failed, 0 skipped, 0 undefined
```

## Next Steps

### Add Real Tests for Diagram Service

Use the complete [diagram analysis example](../examples/diagram_analysis_example.md):

1. **Review the example** - See how features, steps, and environment work together
2. **Copy the patterns** - Use the step definitions template for your tests
3. **Adapt to your needs** - Modify for your specific diagram analysis use cases

### Invoke the Skill

In VS Code Copilot Chat, type:
```
/behavior-test
```

Or ask:
- "Write a BDD test for diagram upload"
- "Create Gherkin scenarios for diagram analysis"
- "Help me write step definitions for my feature"

The agent will load the `behavior-test` skill and guide you through creating BDD tests.

## Common First Tasks

### Task 1: Test Diagram Upload

**Feature:** `features/diagram_upload.feature`
```gherkin
Feature: Diagram Upload
  Validate diagram upload functionality

  Scenario: Upload valid PNG diagram
    Given I have a PNG diagram file
    When I upload the diagram
    Then the upload should succeed
    And I should receive a diagram ID
```

**Steps:** Use patterns from [step_definitions_template.py](../references/step_definitions_template.py)

### Task 2: Test Format Validation

```gherkin
Scenario Outline: Reject invalid formats
  Given I have a diagram with format "<format>"
  When I attempt to upload
  Then I should receive an error
  And the error should mention "unsupported format"
  
  Examples:
    | format |
    | BMP    |
    | GIF    |
    | TIFF   |
```

### Task 3: Test Analysis Results

```gherkin
Scenario: Analyze UML class diagram
  Given I have uploaded a UML class diagram
  When I request analysis
  Then I should receive entities
  And I should receive relationships
  And the diagram type should be "UML Class"
```

## Project Integration

### Running Tests in CI/CD

Add to your test script in `pyproject.toml` or CI configuration:

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run BDD tests
behave

# Or all together
pytest && behave
```

### Coverage

Behave tests complement but don't replace unit/integration tests:

- **Unit tests** (pytest): Fast feedback, implementation testing
- **Integration tests** (pytest): Component interaction testing  
- **BDD tests** (Behave): Acceptance criteria, stakeholder communication

## Tips for Success

1. **Start small** - One feature at a time
2. **Use examples** - Reference the provided templates
3. **Keep scenarios focused** - One behavior per scenario
4. **Think business language** - Write for stakeholders, not developers
5. **Leverage the skill** - Use `/behavior-test` in Copilot Chat for guidance

## Troubleshooting

**"No steps directory found"**
- Make sure you created `features/steps/__init__.py`

**"Step definition not found"**
- Check that step pattern matches exactly
- Verify file is in `features/steps/` directory
- Run `behave --steps` to see loaded step definitions

**"Context attribute not found"**
- Initialize in `before_scenario` hook
- Check previous steps set the required attributes
- Use `@step('debug')` helper from templates

**Tests are too slow**
- Use in-memory adapters instead of real ones
- Avoid sleep() - use proper waits
- Tag slow tests with `@slow` and skip during development

## Resources

- [SKILL.md](../SKILL.md) - Complete skill documentation
- [Step Definitions Template](../references/step_definitions_template.py) - Copy-paste step patterns
- [Environment Template](../references/environment_template.py) - Hooks setup
- [Quick Reference](../references/quick_reference.md) - Behave cheat sheet
- [Complete Example](../examples/diagram_analysis_example.md) - Full working example

## Need Help?

Ask Copilot:
- `/behavior-test help me write a feature for [description]`
- `/behavior-test show me step definitions for [action]`
- `/behavior-test how do I test [scenario]`
