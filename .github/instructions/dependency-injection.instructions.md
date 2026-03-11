---
description: Dependency injection principles for hexagonal architecture
applyTo: 'app/**/*.py'
---

# Dependency Injection

All dependencies must be injected through constructors or function parameters. Never instantiate dependencies directly inside classes or functions except at the composition root (main.py).

## Core Principle

**Inject, don't create.** Classes should receive their dependencies as parameters rather than instantiating them internally.

## Why Dependency Injection

1. **Testability:** Easy to substitute mocks/fakes in tests
2. **Flexibility:** Change implementations without modifying client code
3. **Clarity:** Dependencies are visible in the constructor signature
4. **Hexagonal architecture:** Maintains clean boundaries between layers

## Rules

### ❌ BAD: Creating instances directly

```python
class DiagramService:
    def __init__(self, diagram_id: str):
        self.diagram_id = diagram_id
        # DON'T: Creating dependency inside the class
        self.repository = DiagramRepository()
        self.event_publisher = EventPublisher()
```

```python
class SQSListener:
    def __init__(self, queue_url: str):
        self.queue_url = queue_url
        # DON'T: Creating boto3 client directly
        self.client = boto3.client("sqs", region_name="us-east-1")
```

```python
async def handle_upload(upload: DiagramUpload) -> None:
    # DON'T: Importing and calling function directly
    from app.services.processor import process_diagram
    await process_diagram(upload)
```

### ✅ GOOD: Injecting dependencies

```python
class DiagramService:
    def __init__(
        self,
        diagram_id: str,
        repository: DiagramRepository,
        event_publisher: EventPublisher
    ):
        self.diagram_id = diagram_id
        self.repository = repository
        self.event_publisher = event_publisher
```

```python
class SQSListener:
    def __init__(self, queue_url: str, sqs_client):
        self.queue_url = queue_url
        self.client = sqs_client  # Injected, not created
```

```python
from typing import Callable

class DiagramUploadListener(SQSListener):
    def __init__(
        self,
        queue_url: str,
        sqs_client,
        processor: Callable[[DiagramUpload], None]
    ):
        super().__init__(queue_url, sqs_client)
        self.processor = processor

    def handle_message(self, message: dict) -> None:
        upload = self._parse_message(message)
        self.processor(upload)  # Use injected processor
```

## Layer-Specific Patterns

### Domain Layer

Domain entities should have minimal dependencies:
- Value objects by value
- Other domain entities by reference
- No infrastructure dependencies ever

```python
class DiagramUpload:
    def __init__(self, diagram_id: UUID, folder: str | None = None):
        self.diagram_upload_id = diagram_id
        self.folder = folder
```

### Application Service Layer

Inject all ports (interfaces) that the service needs:

```python
class DiagramAnalysisService:
    def __init__(
        self,
        repository: DiagramRepository,  # Port/interface
        analyzer: DiagramAnalyzer,      # Port/interface
        event_publisher: EventPublisher # Port/interface
    ):
        self.repository = repository
        self.analyzer = analyzer
        self.event_publisher = event_publisher

    async def analyze(self, diagram_id: UUID) -> AnalysisResult:
        diagram = await self.repository.get(diagram_id)
        result = await self.analyzer.analyze(diagram)
        await self.event_publisher.publish(AnalyzedEvent(diagram_id, result))
        return result
```

### Driver Adapters (Event Listeners)

Inject external clients and application services:

```python
class DiagramUploadListener(SQSListener):
    def __init__(
        self,
        queue_url: str,
        sqs_client,                    # AWS SDK client
        upload_processor: Callable     # Application service
    ):
        super().__init__(queue_url, sqs_client)
        self.upload_processor = upload_processor
```

### Driven Adapters (Repositories, Publishers)

Inject infrastructure clients (database connections, AWS clients, etc.):

```python
class S3DiagramRepository:
    def __init__(self, s3_client, bucket_name: str):
        self.s3_client = s3_client  # Injected boto3 client
        self.bucket_name = bucket_name

    async def save(self, diagram: Diagram) -> None:
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=str(diagram.id),
            Body=diagram.content
        )
```

## Composition Root (main.py)

The **only place** where you create and wire dependencies together:

```python
def main() -> None:
    configure_logging()
    settings = Settings()

    # Create infrastructure clients
    sqs_client = boto3.client(
        "sqs",
        region_name=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL
    )

    s3_client = boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL
    )

    # Create driven adapters
    repository = S3DiagramRepository(s3_client, settings.S3_BUCKET)
    event_publisher = SQSEventPublisher(sqs_client, settings.OUTPUT_QUEUE_URL)

    # Create application services
    analysis_service = DiagramAnalysisService(repository, event_publisher)

    # Create driver adapters with all dependencies
    listener = DiagramUploadListener(
        queue_url=settings.SQS_QUEUE_URL,
        sqs_client=sqs_client,
        upload_processor=analysis_service.process_upload
    )

    listener.start()
```

## Testing Benefits

With proper dependency injection, testing becomes straightforward:

```python
def test_diagram_service_calls_repository():
    # Arrange: Mock the dependency
    mock_repo = Mock(spec=DiagramRepository)
    mock_repo.get.return_value = Diagram(id=uuid4(), content="test")

    service = DiagramService(repository=mock_repo)

    # Act
    service.analyze(diagram_id)

    # Assert: Verify interaction
    mock_repo.get.assert_called_once_with(diagram_id)
```

## Exception: Factory Functions

When complex object creation requires multiple steps, use factory functions:

```python
def create_sqs_client(
    region_name: str,
    endpoint_url: str | None = None
) -> boto3.client:
    """Factory function to create configured SQS client."""
    client_kwargs = {"region_name": region_name}
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url
        if not os.environ.get("AWS_ACCESS_KEY_ID"):
            client_kwargs["aws_access_key_id"] = "test"
            client_kwargs["aws_secret_access_key"] = "test"
    return boto3.client("sqs", **client_kwargs)
```

Then in main.py:

```python
def main() -> None:
    settings = Settings()
    sqs_client = create_sqs_client(settings.AWS_REGION, settings.AWS_ENDPOINT_URL)
    listener = DiagramUploadListener(settings.SQS_QUEUE_URL, sqs_client)
```

## Quick Checklist

When writing or reviewing code, ask:

- [ ] Are all dependencies passed as constructor/function parameters?
- [ ] Does the class/function create any external dependencies internally?
- [ ] Can I easily test this with mocks?
- [ ] Is the composition root (main.py) the only place creating concrete instances?
- [ ] Are infrastructure clients (boto3, database connections) injected?
- [ ] Are application services injected into adapters?

## Common Patterns to Avoid

| Anti-Pattern | Why It's Bad | Solution |
|-------------|--------------|----------|
| `boto3.client()` inside `__init__` | Hard to mock for testing | Inject the client |
| `import service; service.process()` | Hidden dependency, tight coupling | Inject the service |
| Creating logger with `logging.getLogger()` in class | Hidden dependency | Inject logger or use structlog with context |
| `Settings()` called in multiple places | Configuration scattered | Create Settings once in main.py, inject values |

## Summary

**One simple rule:** If your class needs it, inject it. The only exception is the composition root (main.py) where all dependencies are wired together.
