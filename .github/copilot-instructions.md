# Diagram Analyzer Service

Python microservice for analyzing diagrams (IADT Phase 5 Hackathon) using hexagonal architecture.

## Environment

- **Python:** 3.12+
- **Package manager:** uv with `pyproject.toml`
- **Install:** `uv sync`
- **Run:** `python main.py`
- **Test:** `pytest`

## Architecture & Conventions

When working with this codebase, follow these context-specific guidelines:

- [Architecture & Structure](instructions/architecture.instructions.md) - Hexagonal architecture layer responsibilities and patterns
- [Python Conventions](instructions/python-conventions.instructions.md) - Project-specific code style and naming
- [Testing Guidelines](instructions/testing.instructions.md) - Test structure, coverage requirements, and when to use skills
- [Dependencies](instructions/dependencies.instructions.md) - Managing project dependencies with uv

## Skills

For implementing features and workflows, use these specialized skills:

- **unit-test** - Write isolated tests for domain, application, or adapter layers
- **integration-test** - Test component interactions across architecture layers
- **behavior-test** - Write BDD tests with Behave using Gherkin scenarios for stakeholder-readable acceptance tests
- **run-diagram-service** - Install, run, test, or develop the service
