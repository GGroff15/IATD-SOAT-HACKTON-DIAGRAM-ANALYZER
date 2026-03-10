---
name: run-diagram-service
description: 'Run, develop, and test the diagram analyzer microservice. Use when starting the service, installing dependencies, running tests, or working with the hexagonal architecture.'
argument-hint: 'Specify action: install, run, test, or develop'
---

# Diagram Analyzer Service

Python microservice for analyzing diagrams using hexagonal architecture.

## When to Use

- Starting the service for the first time
- Running the service in development mode
- Installing or updating dependencies
- Running tests
- Understanding the hexagonal architecture workflow
- Troubleshooting service startup issues

## Prerequisites

- Python 3.12+
- uv package manager installed

## Workflow

### 1. Install Dependencies

First time setup or after dependency changes:

```bash
uv sync
```

This reads `pyproject.toml` and installs all dependencies into `.venv/`.

### 2. Run the Service

Start the main service:

```bash
python main.py
```

The service entry point is in `main.py` at the project root.

### 3. Run Tests

Execute the test suite:

```bash
pytest
```

For coverage report:

```bash
pytest --cov=app --cov-report=html
```

### 4. Development Workflow

When developing new features:

1. **Activate virtual environment** (if not auto-activated):
   - Windows: `.venv\Scripts\Activate.ps1`
   - Unix: `source .venv/bin/activate`

2. **Follow hexagonal architecture layers**:
   - **Domain** (`app/core/domain/`): Pure business logic, no I/O
   - **Application** (`app/core/application/`): Use cases, orchestration
   - **Adapters** (`app/adapter/`):
     - `driver/`: Inbound (event listeners, API handlers)
     - `driven/`: Outbound (persistence, event publishers)

3. **Write tests first** (TDD):
   - Place in `tests/` mirroring `app/` structure
   - Use pytest fixtures and mocks
   - Aim for high coverage of domain and application layers

4. **Run tests after changes**:
   ```bash
   pytest
   ```

## Architecture Reminders

**Domain Layer** (`app/core/domain/`):
- Pure Python classes (entities, value objects)
- No framework dependencies
- No I/O operations

**Application Layer** (`app/core/application/`):
- Orchestrates domain logic
- Defines ports (interfaces) for adapters
- Handles use case workflows

**Adapter Layer** (`app/adapter/`):
- Implements ports defined by application layer
- Handles external I/O (SQS, databases, file systems)
- Keep adapters thin—delegate to services

## Common Commands

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Run service | `python main.py` |
| Run tests | `pytest` |
| Run specific test | `pytest tests/path/to/test.py` |
| Coverage report | `pytest --cov=app --cov-report=html` |
| Add dependency | `uv add <package>` |
| Add dev dependency | `uv add --dev <package>` |

## Troubleshooting

**Import errors**: Ensure virtual environment is activated and dependencies are installed (`uv sync`)

**Test failures**: Check that test structure mirrors app structure and mocks are properly configured

**Architecture violations**: Verify that domain layer has no infrastructure dependencies and adapters implement defined ports
