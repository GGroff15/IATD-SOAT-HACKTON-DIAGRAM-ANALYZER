---
description: Project-specific Python conventions and code style
applyTo: '**/*.py'
---

# Python Conventions

## Project Standards

- **Python version:** 3.12+
- **Line length:** 100 characters maximum
- **Type hints:** Required on all public function signatures
- **Async:** Use for all I/O operations

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files/Modules | snake_case | `diagram_service.py` |
| Classes | PascalCase | `DiagramAnalyzer` |
| Functions/Variables | snake_case | `analyze_diagram()`, `user_count` |
| Constants | UPPER_SNAKE_CASE | `MAX_FILE_SIZE = 10 * 1024 * 1024` |
| Private members | Leading underscore | `_cache`, `_validate()` |

## Type Hints

All public functions must include type hints:

```python
from typing import Optional, List, Dict

def analyze_diagram(
    diagram_id: str,
    include_metadata: bool = True
) -> Dict[str, any]:
    """Analyze a diagram and return results."""
    pass

async def get_diagrams(limit: int = 10) -> List[Diagram]:
    """Fetch multiple diagrams."""
    pass
```

## Import Organization

Three groups, separated by blank lines, sorted alphabetically:

```python
# 1. Standard library
import os
from datetime import datetime
from typing import List, Optional

# 2. Third-party libraries
import boto3
from fastapi import APIRouter

# 3. Local imports (absolute imports only)
from app.core.domain.entities.diagram import Diagram
from app.core.application.services.diagram_service import DiagramService
```

## Code Organization Within Files

1. Module docstring
2. Imports
3. Constants
4. Exception classes
5. Main classes/functions
6. Helper functions (private)

## Error Handling

Use specific exceptions over generic ones:

```python
# Good
raise DiagramNotFoundError(f"Diagram {diagram_id} not found")

# Avoid
raise Exception("Error")
```
