---
description: Testing guidelines, structure, coverage requirements, and pytest patterns
applyTo: 'tests/**/*.py'
---

# Testing Guidelines

## Structure

Mirror `app/` structure in `tests/`:

```
tests/
├── unit/                           # Test individual functions/classes
│   ├── core/
│   │   ├── application/
│   │   │   └── test_diagram_service.py
│   │   └── domain/
│   │       └── test_diagram_entity.py
│   └── adapter/
│       └── driven/
│           └── test_s3_repository.py
├── integration/                    # Test component interactions
│   └── test_diagram_workflow.py
└── e2e/                           # Test full workflows
    └── test_api_endpoints.py
```

## Naming Conventions

### Test Files
```python
test_<module_name>.py
test_diagram_service.py
test_sqs_handler.py
```

### Test Functions
```python
def test_<function>_<scenario>():
    """Test that ..."""
    pass

def test_analyze_diagram_success():
    pass

def test_analyze_diagram_raises_error_when_format_invalid():
    pass
```

## Coverage Requirements

- **Target:** 80%+ coverage
- **Critical paths:** 100% coverage
- **Run with:** `pytest --cov=app tests/`

## Unit Tests

Test individual functions/classes in isolation with mocked dependencies:

```python
# tests/unit/core/application/test_diagram_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.core.application.services.diagram_service import DiagramService
from app.core.application.exceptions import DiagramProcessingError

@pytest.mark.asyncio
async def test_upload_diagram_success():
    # Arrange
    mock_repo = AsyncMock()
    mock_publisher = AsyncMock()
    service = DiagramService(mock_repo, mock_publisher)
    content = b"fake image content"
    
    # Act
    result = await service.upload_diagram(content, "PNG")
    
    # Assert
    assert result.format == "PNG"
    assert result.analyzed is False
    mock_repo.save.assert_called_once()

@pytest.mark.asyncio
async def test_upload_diagram_exceeds_size_limit():
    # Arrange
    service = DiagramService(Mock(), Mock())
    content = b"x" * (11 * 1024 * 1024)  # 11MB
    
    # Act & Assert
    with pytest.raises(DiagramProcessingError, match="exceeds 10MB"):
        await service.upload_diagram(content, "PNG")
```

**Unit Test Rules:**
- Mock all external dependencies
- Test one function/method at a time
- Test both success and error cases
- Use descriptive assertion messages

## Integration Tests

Test interaction between components:

```python
# tests/integration/test_diagram_workflow.py
import pytest
from app.core.application.services.diagram_service import DiagramService
from app.adapter.driven.persistence.file_repository import FileRepository

@pytest.mark.asyncio
async def test_full_diagram_upload_and_retrieval(tmp_path):
    # Use real repository with temp directory
    repo = FileRepository(base_path=str(tmp_path))
    service = DiagramService(repo, None)
    
    # Upload
    diagram = await service.upload_diagram(b"test content", "PNG")
    diagram_id = diagram.id
    
    # Retrieve
    retrieved = await service.get_diagram(diagram_id)
    
    # Verify
    assert retrieved.id == diagram_id
    assert retrieved.content == b"test content"
```

**Integration Test Rules:**
- Use real implementations where practical
- Use temporary resources (files, databases)
- Test realistic workflows
- Clean up resources after tests

## E2E Tests

Test through the API layer:

```python
# tests/e2e/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_upload_and_analyze_diagram():
    # Upload diagram
    files = {"file": ("test.png", b"fake image", "image/png")}
    upload_response = client.post("/diagrams/", files=files)
    assert upload_response.status_code == 201
    diagram_id = upload_response.json()["id"]
    
    # Trigger analysis
    analyze_response = client.post(f"/diagrams/{diagram_id}/analyze")
    assert analyze_response.status_code == 200
    
    # Verify results
    get_response = client.get(f"/diagrams/{diagram_id}")
    assert get_response.json()["analyzed"] is True

def test_upload_invalid_file_type_returns_400():
    files = {"file": ("test.txt", b"text content", "text/plain")}
    response = client.post("/diagrams/", files=files)
    assert response.status_code == 400
    assert "must be an image" in response.json()["detail"]
```

## Pytest Fixtures

Use fixtures for common setup:

```python
# tests/conftest.py
import pytest
from app.core.application.services.diagram_service import DiagramService

@pytest.fixture
def diagram_service():
    """Provide a DiagramService instance with mocked dependencies."""
    from unittest.mock import Mock
    return DiagramService(Mock(), Mock())

@pytest.fixture
def sample_diagram_content():
    """Provide sample diagram content for tests."""
    return b"sample image bytes"

@pytest.fixture
async def uploaded_diagram(diagram_service, sample_diagram_content):
    """Provide an already-uploaded diagram."""
    return await diagram_service.upload_diagram(
        sample_diagram_content, 
        "PNG"
    )
```

**Fixture Scope:**
- `function` (default): New instance per test
- `module`: Shared within module
- `session`: Shared across all tests

## Mocking Best Practices

```python
from unittest.mock import Mock, AsyncMock, patch

# Mock async functions
mock_repo = AsyncMock()
mock_repo.get.return_value = Diagram(...)

# Mock sync functions
mock_logger = Mock()
mock_logger.info.assert_called_with("Expected message")

# Patch external dependencies
@patch('app.adapter.driven.persistence.s3_repository.boto3.client')
def test_s3_upload(mock_boto3):
    mock_s3 = mock_boto3.return_value
    # Test with mocked S3 client
    pass
```

## Parametrized Tests

Test multiple scenarios with one function:

```python
@pytest.mark.parametrize("format,expected", [
    ("PNG", True),
    ("JPG", True),
    ("JPEG", True),
    ("SVG", True),
    ("GIF", False),
])
def test_format_validation(format, expected):
    result = is_valid_format(format)
    assert result == expected
```

## Testing Async Code

Always use `@pytest.mark.asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

## Common Assertion Patterns

```python
# Exact equality
assert result == expected

# Contains
assert "error" in response.json()

# Type checking
assert isinstance(diagram, Diagram)

# Exceptions with context
with pytest.raises(ValueError, match="Invalid format"):
    validate_format("INVALID")

# Mock call verification
mock_repo.save.assert_called_once_with(diagram)
mock_repo.save.assert_not_called()
```

## Test Data Management

Keep test data separate:

```python
# tests/fixtures/sample_diagrams.py
SAMPLE_PNG = b"\x89PNG\r\n..."
SAMPLE_INVALID = b"not an image"

# Use in tests
from tests.fixtures.sample_diagrams import SAMPLE_PNG

def test_with_sample_data():
    result = process_diagram(SAMPLE_PNG)
    assert result is not None
```
