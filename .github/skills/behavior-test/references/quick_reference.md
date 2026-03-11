# Behave Quick Reference

Quick lookup guide for common Behave patterns and commands.

## Running Tests

```bash
# Run all features
behave

# Specific feature
behave features/diagram_analysis.feature

# Specific scenario by line number
behave features/diagram_analysis.feature:15

# With tags
behave --tags=smoke
behave --tags=@smoke,@critical       # AND
behave --tags=@smoke --tags=@api     # OR
behave --tags=~@wip                  # NOT (exclude)

# Verbose output
behave -v
behave --verbose

# Stop on first failure
behave --stop

# Dry run (check syntax)
behave --dry-run

# Show available step definitions
behave --steps

# Generate code snippets for undefined steps
behave --snippets

# Specify format
behave --format=pretty
behave --format=json --outfile=report.json
behave --format=html --outfile=report.html

# Set config values
behave -D browser=chrome -D headless=true

# Parallel execution (requires behave-parallel)
behave --processes 4 --parallel-element scenario
```

## Gherkin Syntax

### Feature
```gherkin
@tag1 @tag2
Feature: Feature name
  Brief description
  of the feature
  
  Background:
    Given common precondition
  
  Scenario: Scenario name
    Given precondition
    When action
    Then outcome
    And additional step
    But exception
```

### Scenario Outline (Data-Driven)
```gherkin
Scenario Outline: Template name
  Given I have <input>
  When I do something
  Then I get <output>
  
  Examples:
    | input | output |
    | value1 | result1 |
    | value2 | result2 |
```

### Doc Strings
```gherkin
Scenario: Multi-line content
  Given a file with content:
    """
    Multi-line
    text content
    goes here
    """
```

### Data Tables
```gherkin
Scenario: Tabular data
  Given these users:
    | name  | role  |
    | Alice | admin |
    | Bob   | user  |
```

## Step Definition Patterns

### Basic Steps
```python
from behave import given, when, then, step

@given('I have a widget')
def step_impl(context):
    context.widget = Widget()

@when('I activate the widget')
def step_impl(context):
    context.result = context.widget.activate()

@then('the widget should be active')
def step_impl(context):
    assert context.widget.is_active()
```

### With Parameters
```python
@given('I have {count:d} apples')
def step_impl(context, count):
    context.apples = count

@given('I have a "{color}" car')
def step_impl(context, color):
    context.car_color = color

# Regex patterns
@given('I have (?P<count>\d+) items')
def step_impl(context, count):
    context.item_count = int(count)
```

### With Tables
```python
@given('the following users')
def step_impl(context):
    for row in context.table:
        name = row['name']
        role = row['role']
        create_user(name, role)
```

### With Doc Strings
```python
@given('a file with content')
def step_impl(context):
    content = context.text
    write_file('test.txt', content)
```

## Context Object

```python
# Set attributes
context.user = User("Alice")
context.result = None
context.temp_files = []

# Access in steps
user_name = context.user.name

# Store configuration
context.config.userdata.get('browser')  # From -D browser=chrome

# Store table data
for row in context.table:
    print(row['column_name'])

# Store doc strings
content = context.text
```

## Environment Hooks

```python
# features/environment.py

def before_all(context):
    """Once before everything"""
    pass

def after_all(context):
    """Once after everything"""
    pass

def before_feature(context, feature):
    """Before each feature file"""
    pass

def after_feature(context, feature):
    """After each feature file"""
    pass

def before_scenario(context, scenario):
    """Before each scenario (most common)"""
    # Set up fresh test data
    context.repository = InMemoryRepository()
    context.service = MyService(context.repository)

def after_scenario(context, scenario):
    """After each scenario (cleanup)"""
    # Clean up resources
    cleanup_temp_files(context.temp_files)
    context.repository.clear()
    
    # Check for failures
    if scenario.status == 'failed':
        print(f"Failed: {scenario.name}")

def before_step(context, step):
    """Before each step (rarely used)"""
    pass

def after_step(context, step):
    """After each step (rarely used)"""
    pass

def before_tag(context, tag):
    """When entering tagged section"""
    if tag == 'skip':
        context.scenario.skip("Skipped via tag")

def after_tag(context, tag):
    """When exiting tagged section"""
    pass
```

## Assertions (hamcrest)

```python
from hamcrest import (
    assert_that, equal_to, is_not, none,
    has_length, greater_than, less_than,
    contains_string, starts_with, ends_with,
    has_key, has_entry, has_item, has_items,
    is_in, all_of, any_of
)

# Equality
assert_that(actual, equal_to(expected))
assert_that(value, is_not(none()))

# Comparisons
assert_that(count, greater_than(5))
assert_that(age, less_than(100))

# Strings
assert_that(message, contains_string("error"))
assert_that(text, starts_with("Hello"))
assert_that(filename, ends_with(".txt"))

# Collections
assert_that(items, has_length(3))
assert_that([1, 2, 3], has_item(2))
assert_that([1, 2, 3], has_items(1, 3))

# Dictionaries
assert_that(data, has_key('name'))
assert_that(data, has_entry('name', 'Alice'))

# Membership
assert_that(value, is_in([1, 2, 3]))

# Combinators
assert_that(x, all_of(greater_than(0), less_than(10)))
assert_that(x, any_of(equal_to(5), equal_to(10)))
```

## Tags

```gherkin
# Feature level
@smoke @api
Feature: API Tests

# Scenario level
@critical @happy-path
Scenario: Success case

# Multiple scenarios
@smoke
Scenario: Test 1

@wip @skip
Scenario: Test 2
```

### Common Tag Conventions
- `@smoke` - Quick smoke tests
- `@wip` - Work in progress
- `@skip` - Skip this test
- `@slow` - Long-running test
- `@manual` - Manual test only
- `@bug-123` - Related to bug #123
- `@fixture-cleanup` - Requires special cleanup
- `@integration` - Integration test
- `@unit` - Unit test
- `@e2e` - End-to-end test

## Configuration

### behave.ini
```ini
[behave]
format = pretty
color = true
show_skipped = false
show_timings = true
junit = true
junit_directory = test-reports
```

### Environment Variables
```python
# In features/environment.py
import os

def before_all(context):
    context.base_url = os.getenv('BASE_URL', 'http://localhost:8000')
    context.timeout = int(os.getenv('TIMEOUT', '30'))
```

## Common Patterns

### Setup/Teardown Pattern
```python
def before_scenario(context, scenario):
    # Setup
    context.db = create_test_db()
    context.client = create_client()

def after_scenario(context, scenario):
    # Teardown
    context.db.close()
    context.client.disconnect()
```

### Skip on Condition
```python
def before_scenario(context, scenario):
    if 'requires-aws' in scenario.tags:
        if not os.getenv('AWS_CONFIGURED'):
            scenario.skip("AWS not configured")
```

### Capture Failures
```python
def after_scenario(context, scenario):
    if scenario.status == 'failed':
        # Take screenshot, save logs, etc.
        save_screenshot(f"failure_{scenario.name}.png")
        save_logs(context.logs)
```

### Shared State
```python
@given('I am logged in as admin')
def step_impl(context):
    context.user = login('admin', 'password')
    context.auth_token = context.user.token

@when('I make an authenticated request')
def step_impl(context):
    response = requests.get(
        '/api/data',
        headers={'Authorization': f'Bearer {context.auth_token}'}
    )
    context.response = response
```

## Debugging

```python
# Print context for debugging
@step('debug')
def step_debug(context):
    import pprint
    pprint.pprint(vars(context))

# Python debugger
@when('I do something complex')
def step_impl(context):
    import pdb; pdb.set_trace()  # Breakpoint
    # ... step code
```

## Best Practices Summary

1. ✓ Write scenarios from user/business perspective
2. ✓ Keep steps reusable and composable
3. ✓ Use declarative style (what, not how)
4. ✓ One scenario = one behavior
5. ✓ Clean up in hooks, not steps
6. ✓ Use tags for organization
7. ✓ Keep scenarios short (<10 steps)
8. ✓ Use Scenario Outline for data variations
9. ✓ Make step definitions atomic
10. ✓ Avoid technical implementation details in Gherkin

## Anti-Patterns to Avoid

1. ✗ UI-focused steps ("click button", "fill field")
2. ✗ Implementation details in scenarios
3. ✗ Testing multiple behaviors in one scenario
4. ✗ Copy-pasting step definitions
5. ✗ Using sleep() excessively
6. ✗ Hard-coded test data
7. ✗ Scenarios dependent on execution order
8. ✗ Overly complex step definitions
9. ✗ Sharing mutable state without cleanup
10. ✗ Testing through the UI when API is available
