---
name: unit-test
description: 'Write unit tests for the diagram analyzer service following hexagonal architecture patterns. Use when writing tests for domain entities, application services, or adapters with proper mocking and isolation.'
argument-hint: 'Specify layer: domain, application, driver, or driven'
---

# Unit Testing for Hexagonal Architecture

Write isolated, fast unit tests using pytest with proper mocking strategies for each architecture layer.

Write tests before write production code to follow TDD principles. Focus on testing business logic in the domain layer without mocks, and orchestration logic in the application layer with mocked dependencies. For adapters, mock external resources to test adapter implementation in isolation.

## When to Use This Skill

- Writing tests for new domain entities or value objects
- Testing application services with mocked dependencies
- Testing adapters (event listeners, repositories, publishers)
- Following TDD (Test-Driven Development)
- Ensuring >80% code coverage
- Debugging failing tests
- Need examples of mocking patterns for specific layers

## Test Structure Pattern

All unit tests follow **AAA (Arrange-Act-Assert)** structure:

```python
def test_function_name_scenario():
    """Test that [specific behavior]."""
    # Arrange: Set up test data and mocks
    
    # Act: Execute the function under test
    
    # Assert: Verify the outcome
```

## Layer-Specific Testing Patterns

### Domain Layer Tests (Zero Mocking)

**Location:** `tests/unit/core/domain/`

Domain tests require **no mocking** - test pure business logic in isolation.

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

**Domain Testing Checklist:**
- ✓ No mocks needed
- ✓ Test all business rules
- ✓ Test edge cases and validation
- ✓ Fast execution (<1ms per test)
- ✓ Test value object immutability
- ✓ Test entity state transitions

### Application Layer Tests (Mock All Adapters)

**Location:** `tests/unit/core/application/`

Application tests must **mock all adapters** to test orchestration logic in isolation.

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

**Application Testing Checklist:**
- ✓ Mock ALL dependencies (repositories, publishers, external services)
- ✓ Test orchestration logic, not implementation details
- ✓ Verify interactions with mocks using `assert_called_once_with()`
- ✓ Test both success and error paths
- ✓ Use descriptive test names that explain the scenario
- ✓ Test transaction boundaries
- ✓ Test error handling and rollback logic

### Driver Adapter Tests (Mock Application Services)

**Location:** `tests/unit/adapter/driver/`

Driver adapter tests **mock application services** to test message parsing and delegation.

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

@pytest.mark.asyncio
async def test_handle_missing_required_field_raises_error():
    """Test that missing required fields raise validation error."""
    # Arrange
    incomplete_message = {"diagram_id": "123"}  # missing bucket and key
    
    # Act & Assert
    with pytest.raises(KeyError):
        await handle_diagram_upload(incomplete_message)
```

**Driver Adapter Testing Checklist:**
- ✓ Keep handlers thin (just parse and delegate)
- ✓ Mock the application service
- ✓ Test message parsing logic
- ✓ Test error handling (invalid formats, missing fields)
- ✓ Verify logging for troubleshooting
- ✓ Test all message format variations

### Driven Adapter Tests (Mock External Resources)

**Location:** `tests/unit/adapter/driven/`

Driven adapter tests **mock external resources** to test adapter implementation without I/O.

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

@pytest.mark.asyncio
async def test_save_handles_io_error_gracefully():
    """Test that I/O errors are handled with proper exceptions."""
    # Arrange
    repo = FileRepository(base_path="/tmp/diagrams")
    diagram = Mock(id="test", content=b"data", format="PNG")
    
    # Act & Assert
    with patch("builtins.open", side_effect=IOError("Disk full")):
        with pytest.raises(IOError, match="Disk full"):
            await repo.save(diagram)
```

**Driven Adapter Testing Checklist:**
- ✓ Mock I/O operations (file, network, database)
- ✓ Test the adapter's implementation of the port interface
- ✓ Don't test external libraries (boto3, sqlalchemy)
- ✓ Use `pytest.raises` for expected errors
- ✓ Test error handling and retry logic
- ✓ Test data format conversion (domain ↔ external)

## Common Testing Patterns

### Async Testing

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Parameterized Tests

Test multiple scenarios with one test function:

```python
@pytest.mark.parametrize("format_type,expected", [
    ("PNG", True),
    ("JPG", True),
    ("SVG", False),
    ("GIF", True),
])
def test_is_raster_format(format_type, expected):
    """Test format detection for multiple types."""
    assert is_raster_format(format_type) == expected
```

### Exception Testing

```python
# Test specific exception type and message
def test_raises_specific_error():
    with pytest.raises(ValueError, match="Invalid format"):
        validate_format("INVALID")

# Test that no exception is raised
def test_does_not_raise():
    try:
        validate_format("PNG")
    except Exception:
        pytest.fail("Should not raise exception")
```

### Mock Return Values and Side Effects

```python
# Simple return value
mock_repo.get.return_value = some_object

# Different returns on successive calls
mock_repo.list.side_effect = [[], [obj1], [obj1, obj2]]

# Raise an exception
mock_service.process.side_effect = ValueError("Error")

# Call a function
mock_handler.handle.side_effect = lambda x: x.upper()
```

### Verify Mock Calls

```python
# Called once with no arguments
mock_service.method.assert_called_once()

# Called once with specific arguments
mock_service.method.assert_called_once_with(arg1, arg2, kwarg=value)

# Never called
mock_service.method.assert_not_called()

# Called specific number of times
assert mock_service.method.call_count == 3

# Check call arguments for any call
calls = mock_service.method.call_args_list
assert calls[0][0][0] == "first argument of first call"

# Verify call order
mock_manager = Mock()
mock_manager.attach_mock(mock_repo, 'repo')
mock_manager.attach_mock(mock_publisher, 'publisher')
expected_calls = [call.repo.save(diagram), call.publisher.publish(event)]
assert mock_manager.mock_calls == expected_calls
```

## Shared Fixtures

Create common fixtures in `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
from datetime import datetime
from app.core.domain.entities.diagram import Diagram

@pytest.fixture
def sample_diagram_content():
    """Provide sample binary content for tests."""
    return b"fake image bytes for testing"

@pytest.fixture
def diagram_id():
    """Provide a consistent diagram ID."""
    return "test-diagram-123"

@pytest.fixture
def sample_diagram(diagram_id, sample_diagram_content):
    """Provide a pre-constructed diagram entity."""
    return Diagram(
        id=diagram_id,
        content=sample_diagram_content,
        format="PNG",
        created_at=datetime.now()
    )

@pytest.fixture
def mock_async_repository():
    """Provide a mocked async repository."""
    from unittest.mock import AsyncMock
    return AsyncMock()
```

## Running Unit Tests

```bash
# Run all unit tests
pytest tests/unit/

# Run tests for specific layer
pytest tests/unit/core/domain/
pytest tests/unit/core/application/
pytest tests/unit/adapter/

# Run specific test file
pytest tests/unit/core/application/test_diagram_service.py

# Run specific test
pytest tests/unit/core/application/test_diagram_service.py::test_upload_diagram_success

# With coverage
pytest tests/unit/ --cov=app --cov-report=term-missing

# Verbose output
pytest tests/unit/ -v

# Stop on first failure
pytest tests/unit/ -x
```

## Troubleshooting

**Import errors in tests:**
- Ensure virtual environment is activated
- Run `uv sync` to install dependencies
- Check that test file mirrors app structure

**Mocks not working:**
- Verify patch path matches import path in the code under test
- Use `AsyncMock` for async functions, not regular `Mock`
- Check that mock is set up before calling the function

**Async test failures:**
- Add `@pytest.mark.asyncio` decorator
- Use `AsyncMock` for async dependencies
- Ensure `pytest-asyncio` is installed

**Fixture not found:**
- Check fixture is defined in `conftest.py` or same file
- Verify fixture name matches parameter name exactly
- Check fixture scope (function, module, session)
