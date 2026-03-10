---
name: unit-test
description: 'Write unit tests for the diagram analyzer service following hexagonal architecture patterns. Use when writing tests for domain entities, application services, or adapters with proper mocking and isolation.'
argument-hint: 'Specify layer: domain, application, driver, or driven'
---

# Unit Testing for Hexagonal Architecture

Write isolated, fast unit tests for the diagram analyzer service using pytest and proper mocking strategies.

## When to Use

- Writing tests for new domain entities or value objects
- Testing application services with mocked dependencies
- Testing adapters (event listeners, repositories, publishers)
- Following TDD (Test-Driven Development)
- Ensuring >80% code coverage
- Debugging failing tests

## Workflow

### 1. Identify the Layer

Determine which layer your code belongs to, as each has different testing approaches:

| Layer | Location | Dependencies to Mock |
|-------|----------|---------------------|
| Domain | `app/core/domain/` | None (pure logic) |
| Application | `app/core/application/` | All adapters (repos, publishers) |
| Driver Adapter | `app/adapter/driver/` | Application services |
| Driven Adapter | `app/adapter/driven/` | External resources (DB, SQS, filesystem) |

### 2. Create Test File

Mirror the app structure in `tests/unit/`:

```
app/core/application/services/diagram_service.py
→ tests/unit/core/application/test_diagram_service.py

app/adapter/driven/persistence/file_repository.py
→ tests/unit/adapter/driven/persistence/test_file_repository.py
```

**Naming:** `test_<module_name>.py`

### 3. Write Test Using AAA Pattern

**Arrange-Act-Assert** structure for every test:

```python
def test_function_name_scenario():
    """Test that [specific behavior]."""
    # Arrange: Set up test data and mocks
    
    # Act: Execute the function under test
    
    # Assert: Verify the outcome
```

### 4. Follow Layer-Specific Patterns

See detailed patterns below for each layer.

## Domain Layer Tests

**Zero mocking required** - test pure business logic in isolation.

```python
# tests/unit/core/domain/test_diagram.py
from datetime import datetime
from app.core.domain.entities.diagram import Diagram

def test_diagram_creation():
    """Test that a Diagram can be instantiated with valid data."""
    # Arrange
    diagram_id = "diag-123"
    content = b"fake image bytes"
    format_type = "PNG"
    created = datetime.now()
    
    # Act
    diagram = Diagram(
        id=diagram_id,
        content=content,
        format=format_type,
        created_at=created
    )
    
    # Assert
    assert diagram.id == diagram_id
    assert diagram.content == content
    assert diagram.format == format_type
    assert diagram.analyzed is False  # default value

def test_diagram_mark_as_analyzed():
    """Test that marking a diagram as analyzed updates the state."""
    # Arrange
    diagram = Diagram("id", b"content", "PNG", datetime.now())
    
    # Act
    diagram.mark_as_analyzed()
    
    # Assert
    assert diagram.analyzed is True

def test_invalid_format_raises_error():
    """Test that invalid format raises ValueError."""
    # Arrange & Act & Assert
    with pytest.raises(ValueError, match="Invalid format"):
        Diagram("id", b"content", "INVALID", datetime.now())
```

**Domain Testing Rules:**
- No mocks needed
- Test all business rules
- Test edge cases and validation
- Fast execution (<1ms per test)

## Application Layer Tests

**Mock all adapters** - test orchestration logic in isolation.

```python
# tests/unit/core/application/test_diagram_service.py
import pytest
from unittest.mock import Mock, AsyncMock, call
from app.core.application.services.diagram_service import DiagramService
from app.core.application.exceptions import DiagramNotFoundError
from app.core.domain.entities.diagram import Diagram

@pytest.fixture
def mock_repository():
    """Provide a mocked repository."""
    return AsyncMock()

@pytest.fixture
def mock_publisher():
    """Provide a mocked event publisher."""
    return AsyncMock()

@pytest.fixture
def diagram_service(mock_repository, mock_publisher):
    """Provide a DiagramService with mocked dependencies."""
    return DiagramService(mock_repository, mock_publisher)

@pytest.mark.asyncio
async def test_upload_diagram_saves_and_publishes_event(
    diagram_service,
    mock_repository,
    mock_publisher
):
    """Test that uploading a diagram saves it and publishes an event."""
    # Arrange
    content = b"test image content"
    format_type = "PNG"
    
    # Act
    result = await diagram_service.upload_diagram(content, format_type)
    
    # Assert
    assert result.format == format_type
    assert result.content == content
    mock_repository.save.assert_called_once_with(result)
    mock_publisher.publish.assert_called_once_with(
        "diagram.uploaded",
        {"diagram_id": result.id}
    )

@pytest.mark.asyncio
async def test_upload_diagram_exceeds_size_limit_raises_error(diagram_service):
    """Test that uploading oversized content raises an error."""
    # Arrange
    content = b"x" * (11 * 1024 * 1024)  # 11MB
    
    # Act & Assert
    with pytest.raises(ValueError, match="exceeds 10MB"):
        await diagram_service.upload_diagram(content, "PNG")

@pytest.mark.asyncio
async def test_get_diagram_not_found_raises_error(
    diagram_service,
    mock_repository
):
    """Test that getting a non-existent diagram raises DiagramNotFoundError."""
    # Arrange
    mock_repository.get.return_value = None
    
    # Act & Assert
    with pytest.raises(DiagramNotFoundError):
        await diagram_service.get_diagram("nonexistent-id")

@pytest.mark.asyncio
async def test_analyze_diagram_workflow(
    diagram_service,
    mock_repository,
    mock_publisher
):
    """Test the complete diagram analysis workflow."""
    # Arrange
    diagram = Diagram("id-123", b"content", "PNG", datetime.now())
    mock_repository.get.return_value = diagram
    
    # Act
    result = await diagram_service.analyze_diagram("id-123")
    
    # Assert - verify orchestration
    assert result["diagram_id"] == "id-123"
    assert diagram.analyzed is True
    mock_repository.save.assert_called_once_with(diagram)
    mock_publisher.publish.assert_called_once_with(
        "diagram.analyzed",
        result
    )
```

**Application Testing Rules:**
- Mock ALL dependencies (repositories, publishers, external services)
- Test orchestration logic, not implementation details
- Verify interactions with mocks (`assert_called_once_with`)
- Test both success and error paths
- Use descriptive test names that explain the scenario

## Driver Adapter Tests (Event Listeners, Handlers)

**Mock application services** - test message parsing and delegation.

```python
# tests/unit/adapter/driver/event_listeners/test_sqs_handler.py
import pytest
from unittest.mock import AsyncMock, patch
from app.adapter.driver.event_listeners.sqs_handler import handle_diagram_upload

@pytest.mark.asyncio
async def test_handle_diagram_upload_delegates_to_service():
    """Test that SQS handler parses message and delegates to service."""
    # Arrange
    message = {
        "diagram_id": "diag-456",
        "s3_bucket": "my-bucket",
        "s3_key": "diagrams/image.png"
    }
    mock_service = AsyncMock()
    
    # Act
    with patch("app.adapter.driver.event_listeners.sqs_handler.get_service") as mock_get:
        mock_get.return_value = mock_service
        await handle_diagram_upload(message)
    
    # Assert
    mock_service.process_uploaded_diagram.assert_called_once_with(
        diagram_id="diag-456",
        bucket="my-bucket",
        key="diagrams/image.png"
    )

@pytest.mark.asyncio
async def test_handle_invalid_message_logs_error():
    """Test that invalid message format logs error and doesn't crash."""
    # Arrange
    invalid_message = {"wrong_key": "value"}
    
    # Act & Assert
    with patch("app.adapter.driver.event_listeners.sqs_handler.logger") as mock_logger:
        await handle_diagram_upload(invalid_message)
        mock_logger.error.assert_called_once()
```

**Driver Testing Rules:**
- Keep handlers thin (just parse and delegate)
- Mock the application service
- Test message parsing logic
- Test error handling (invalid formats, missing fields)
- Verify logging for troubleshooting

## Driven Adapter Tests (Repositories, Publishers)

**Mock external resources** - test adapter implementation without I/O.

```python
# tests/unit/adapter/driven/persistence/test_file_repository.py
import pytest
from unittest.mock import Mock, patch, mock_open
from app.adapter.driven.persistence.file_repository import FileRepository

@pytest.mark.asyncio
async def test_save_diagram_writes_file():
    """Test that saving a diagram writes to the filesystem."""
    # Arrange
    repo = FileRepository(base_path="/tmp/diagrams")
    diagram = Mock(id="diag-789", content=b"image data", format="PNG")
    
    # Act
    with patch("builtins.open", mock_open()) as mock_file:
        with patch("os.makedirs") as mock_mkdir:
            await repo.save(diagram)
    
    # Assert
    mock_mkdir.assert_called_once_with("/tmp/diagrams", exist_ok=True)
    mock_file.assert_called_once_with("/tmp/diagrams/diag-789.png", "wb")
    mock_file().write.assert_called_once_with(b"image data")

@pytest.mark.asyncio
async def test_get_diagram_reads_file():
    """Test that getting a diagram reads from filesystem."""
    # Arrange
    repo = FileRepository(base_path="/tmp/diagrams")
    expected_content = b"stored image"
    
    # Act
    with patch("builtins.open", mock_open(read_data=expected_content)):
        with patch("os.path.exists", return_value=True):
            diagram = await repo.get("diag-789")
    
    # Assert
    assert diagram.content == expected_content

@pytest.mark.asyncio
async def test_get_nonexistent_diagram_returns_none():
    """Test that getting missing diagram returns None."""
    # Arrange
    repo = FileRepository(base_path="/tmp/diagrams")
    
    # Act
    with patch("os.path.exists", return_value=False):
        result = await repo.get("missing-id")
    
    # Assert
    assert result is None
```

**Driven Testing Rules:**
- Mock I/O operations (file, network, database)
- Test the adapter's implementation of the port interface
- Don't test external libraries (boto3, sqlalchemy)
- Use `pytest.raises` for expected errors

## Common Patterns

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Parameterized Tests

```python
@pytest.mark.parametrize("format_type,expected", [
    ("PNG", True),
    ("JPG", True),
    ("SVG", False),
])
def test_is_raster_format(format_type, expected):
    assert is_raster_format(format_type) == expected
```

### Exception Testing

```python
def test_raises_specific_error():
    with pytest.raises(ValueError, match="Invalid format"):
        validate_format("INVALID")
```

### Mock Return Values

```python
mock_repo.get.return_value = some_object
mock_repo.list.side_effect = [[], [obj1], [obj1, obj2]]
```

### Verify Mock Calls

```python
mock_service.method.assert_called_once()
mock_service.method.assert_called_once_with(arg1, arg2)
mock_service.method.assert_not_called()
assert mock_service.method.call_count == 3
```

## Fixtures in conftest.py

Create shared fixtures in `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
from datetime import datetime

@pytest.fixture
def sample_diagram_content():
    """Provide sample binary content for tests."""
    return b"fake image bytes for testing"

@pytest.fixture
def diagram_id():
    """Provide a consistent diagram ID."""
    return "test-diagram-123"

@pytest.fixture
def current_timestamp():
    """Provide a fixed timestamp for reproducible tests."""
    return datetime(2026, 3, 10, 12, 0, 0)
```

## Coverage Commands

```bash
# Run tests with coverage
pytest --cov=app tests/

# Generate HTML report
pytest --cov=app --cov-report=html tests/

# Show missing lines
pytest --cov=app --cov-report=term-missing tests/

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=80 tests/
```

## Test Quality Checklist

- [ ] Test name describes the scenario clearly
- [ ] Follows Arrange-Act-Assert pattern
- [ ] Docstring explains what is being tested
- [ ] Mocks are properly configured with expected behavior
- [ ] Both success and error cases tested
- [ ] Tests are independent (no shared state)
- [ ] Tests run fast (<10ms for unit tests)
- [ ] Assertions are specific and meaningful
- [ ] No actual I/O operations (files, network, DB)

## Anti-Patterns to Avoid

❌ **Testing implementation details**
```python
# Bad: Testing internal structure
assert service._cache["key"] == value
```

✅ **Test behavior**
```python
# Good: Testing observable behavior
assert service.get("key") == value
```

❌ **Multiple responsibilities per test**
```python
# Bad: Testing too much
def test_everything():
    test_upload()
    test_download()
    test_delete()
```

✅ **One scenario per test**
```python
# Good: Focused tests
def test_upload_success(): ...
def test_download_returns_content(): ...
def test_delete_removes_file(): ...
```

❌ **Real I/O in unit tests**
```python
# Bad: Actually writing files
with open("test.txt", "w") as f:
    f.write("data")
```

✅ **Mock I/O operations**
```python
# Good: Mocked I/O
with patch("builtins.open", mock_open()):
    # test code
```
