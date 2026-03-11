---
description: Hexagonal architecture patterns and layer responsibilities for the diagram analyzer service
applyTo: 'app/**/*.py'
---

# Hexagonal Architecture

This project follows hexagonal architecture (ports and adapters pattern) with three distinct layers.

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
    ├── driver/                    # Inbound adapters (receive requests)
    │   └── event_listeners/      # SQS handlers, message consumers
    └── driven/                    # Outbound adapters (external interactions)
        ├── persistence/          # Data storage (filesystem, DB)
        └── event_publishers/     # Event emitters (SQS, etc.)
```

## Layer Responsibilities

### Domain Layer (`app/core/domain/`)

**Pure business logic with zero infrastructure dependencies**

- Domain entities (core business objects)
- Value objects (immutable domain concepts)
- Business rules and invariants
- No I/O operations, no framework dependencies
- Easily testable in complete isolation

**Use when:** Modeling core business concepts that exist independent of technology.

### Application Service Layer (`app/core/application/`)

**Orchestrates domain logic and coordinates with adapters**

- Use case implementations
- Workflow orchestration across domain and adapters
- Defines ports (interfaces) for adapters to implement
- Transaction boundary management
- Domain exception handling

**Use when:** Implementing end-to-end business workflows that coordinate multiple components.

### Driver Adapters (`app/adapter/driver/`)

**Inbound - receive requests from the external world**

- Event listeners (SQS, Kafka)
- Message consumers
- Keep handlers thin - parse input, delegate to application services
- Handle framework-specific concerns

**Use when:** Receiving external input that triggers use cases.

### Driven Adapters (`app/adapter/driven/`)

**Outbound - interact with external systems**

- Repositories (persistence)
- Event publishers (SQS, SNS)
- External API clients
- Implement ports defined by application layer
- Convert between domain entities and external formats

**Use when:** Persisting data, publishing events, or calling external services.

## Dependency Rules

**Critical: Dependencies flow inward only**

```
Adapters → Application → Domain
```

- Domain depends on nothing (pure logic)
- Application depends only on domain
- Adapters depend on application and domain
- Inject adapters into application services (dependency inversion)

## Error Handling

Define domain-specific exceptions in `app/core/application/exceptions.py`:

```python
class DiagramAnalyzerException(Exception):
    """Base exception for this service"""

class DiagramNotFoundError(DiagramAnalyzerException):
    """Diagram doesn't exist"""

class InvalidDiagramFormatError(DiagramAnalyzerException):
    """Diagram format is unsupported"""
```

**Validation layers:**
- Input validation: In adapters (Pydantic for API)
- Business rules: In domain/application layer
- Data integrity: In persistence layer

## Technology Boundaries

**Pydantic models:** Use only in API adapters for request/response schemas. Never in domain layer.

**Domain entities:** Use dataclasses or plain classes, not Pydantic models.

## When Working With This Architecture

- Adding new entity? → `app/core/domain/entities/`
- Adding new use case? → `app/core/application/services/`
- Processing external events? → `app/adapter/driver/event_listeners/`
- Storing data? → `app/adapter/driven/persistence/`
- Publishing events? → `app/adapter/driven/event_publishers/`

For implementing features, use the **run-diagram-service** skill to understand the development workflow.
