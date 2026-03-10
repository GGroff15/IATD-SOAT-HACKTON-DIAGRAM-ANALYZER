---
description: Hexagonal architecture patterns and layer responsibilities for the diagram analyzer service
applyTo: 'app/**/*.py'
---

# Hexagonal Architecture

## Layer Structure

```
app/
├── core/
│   ├── application/               # Application services (use cases)
│   │   ├── services/             # Business logic orchestration
│   │   ├── factory/              # Complex entity creation
│   │   └── exceptions.py         # Domain exceptions
│   └── domain/                    # Pure domain logic
│       ├── entities/             # Domain entities
│       └── value_objects/        # Value objects
└── adapter/
    ├── driver/                    # Inbound adapters
    │   └── event_listeners/      # SQS handlers, message consumers
    └── driven/                    # Outbound adapters
        ├── persistence/          # Data storage (filesystem, DB)
        └── event_publishers/     # Event emitters (SQS, etc.)
```

## Layer Responsibilities

### Domain Layer (`app/core/domain/`)

**Pure business logic - no dependencies on infrastructure**

```python
# app/core/domain/entities/diagram.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Diagram:
    """Domain entity representing a diagram."""
    id: str
    content: bytes
    format: str
    created_at: datetime
    analyzed: bool = False
```

**Rules:**
- No I/O operations
- No framework dependencies
- No infrastructure concerns
- Easily testable in isolation

### Application Service Layer (`app/core/application/`)

**Orchestrates domain logic and coordinates with adapters**

```python
# app/core/application/services/diagram_service.py
class DiagramService:
    def __init__(self, diagram_repo, event_publisher):
        self.diagram_repo = diagram_repo
        self.event_publisher = event_publisher
    
    async def analyze_diagram(self, diagram_id: str) -> dict:
        # Orchestrate: fetch, analyze, save, publish event
        diagram = await self.diagram_repo.get(diagram_id)
        result = self._perform_analysis(diagram)
        await self.diagram_repo.save(diagram)
        await self.event_publisher.publish("diagram.analyzed", result)
        return result
```

**Rules:**
- Contains use case logic
- Coordinates between domain and adapters
- Defines interfaces (ports) for adapters
- Handles transactions
- Throws domain exceptions

### Driver Adapters (`app/adapter/driver/`)

**Inbound - receive requests from external world**

#### Event Listeners (`app/adapter/driver/event_listeners/`)

```python
# app/adapter/driver/event_listeners/sqs_handler.py
async def handle_diagram_upload_event(message: dict):
    # Parse message, delegate to service
    service = DiagramService()
    await service.process_upload(message['diagram_id'])
```

**Rules:**
- Keep handlers thin
- Delegate to application services
- Handle message parsing/validation
- Log errors appropriately

### Driven Adapters (`app/adapter/driven/`)

**Outbound - interact with external systems**

#### Persistence (`app/adapter/driven/persistence/`)

```python
# app/adapter/driven/persistence/diagram_repository.py
class DiagramRepository:
    async def save(self, diagram: Diagram) -> None:
        # Save to filesystem, S3, database, etc.
        pass
    
    async def get(self, diagram_id: str) -> Diagram:
        # Retrieve and reconstruct domain entity
        pass
```

**Rules:**
- Implement interfaces defined by application layer
- Convert between domain entities and storage format
- Handle storage-specific errors

#### Event Publishers (`app/adapter/driven/event_publishers/`)

```python
# app/adapter/driven/event_publishers/sqs_publisher.py
class SQSPublisher:
    async def publish(self, event_type: str, payload: dict) -> None:
        # Send to SQS, Kafka, etc.
        pass
```

## Dependency Flow

**Dependency direction: Adapter → Application → Domain**

- Domain depends on nothing
- Application depends only on domain
- Adapters depend on application and domain
- Inject adapters into application services

```python
# Dependency injection example
diagram_repo = S3DiagramRepository()
event_publisher = SQSPublisher()
diagram_service = DiagramService(diagram_repo, event_publisher)
```

## Common Patterns

### Error Handling

Define domain exceptions in `app/core/application/exceptions.py`:

```python
class DiagramAnalyzerException(Exception):
    """Base exception"""

class DiagramNotFoundError(DiagramAnalyzerException):
    """Raised when diagram doesn't exist"""

class InvalidDiagramFormatError(DiagramAnalyzerException):
    """Raised when format is invalid"""
```

### Validation

- **Input validation:** In adapters (Pydantic for API)
- **Business rules:** In domain/application layer
- **Data integrity:** In persistence layer

### Pydantic Models

Use only in API adapter for request/response:

```python
# app/adapter/driver/api/schemas/diagram.py
from pydantic import BaseModel

class DiagramResponse(BaseModel):
    id: str
    format: str
    analyzed: bool
```

**Don't** use Pydantic in domain layer - use dataclasses or plain classes.
