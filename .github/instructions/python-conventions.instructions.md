---
description: Python code style, naming conventions, type hints, and PEP 8 standards
applyTo: '**/*.py'
---

# Python Conventions

## Style Standards

- **PEP 8 compliant**
- **Line length:** 100 characters max
- **Python version:** 3.12+

## Type Hints

Use type annotations for all function signatures:

```python
from typing import Optional, List, Dict

def analyze_diagram(
    diagram_id: str,
    include_metadata: bool = True
) -> Dict[str, any]:
    """Analyze a diagram and return results."""
    pass

async def get_diagrams(
    limit: int = 10
) -> List[Diagram]:
    """Fetch multiple diagrams."""
    pass
```

**Rules:**
- All public functions must have type hints
- Use `Optional[T]` for nullable parameters
- Use `List`, `Dict`, `Set` from `typing` for collections
- Return types required, even for `None` (use `-> None`)

## Naming Conventions

### Files and Modules
```python
# snake_case.py
diagram_service.py
sqs_publisher.py
```

### Classes
```python
# PascalCase
class DiagramAnalyzer:
    pass

class SQSEventPublisher:
    pass
```

### Functions and Variables
```python
# snake_case
def analyze_diagram():
    pass

diagram_count = 10
user_input = "test"
```

### Constants
```python
# UPPER_SNAKE_CASE
MAX_FILE_SIZE = 10 * 1024 * 1024
DEFAULT_TIMEOUT = 30
SUPPORTED_FORMATS = ["PNG", "JPG", "SVG"]
```

### Private Members
```python
class DiagramService:
    def __init__(self):
        self._cache = {}  # Private attribute
    
    def _validate(self):  # Private method
        pass
```

## Import Organization

Group imports in three sections, separated by blank lines:

```python
# 1. Standard library
import os
import sys
from datetime import datetime
from typing import List, Optional

# 2. Third-party libraries
import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 3. Local imports
from app.core.domain.entities.diagram import Diagram
from app.core.application.services.diagram_service import DiagramService
from app.core.application.exceptions import DiagramNotFoundError
```

**Rules:**
- Sort alphabetically within each group
- Use absolute imports for local modules
- Avoid wildcard imports (`from module import *`)

## Docstrings

Use Google-style docstrings:

```python
def analyze_diagram(diagram_id: str, options: dict) -> dict:
    """
    Analyze a diagram and extract components.
    
    Args:
        diagram_id: Unique identifier for the diagram
        options: Analysis options (e.g., {'ocr': True})
    
    Returns:
        Dictionary containing analysis results with keys:
        - entities: List of detected entities
        - relationships: List of relationships between entities
    
    Raises:
        DiagramNotFoundError: If diagram doesn't exist
        InvalidDiagramFormatError: If diagram format is unsupported
    """
    pass
```

## Error Handling

Prefer specific exceptions over generic ones:

```python
# Good
raise DiagramNotFoundError(f"Diagram {diagram_id} not found")

# Avoid
raise Exception("Error")
```

## Async/Await

Use async for I/O operations:

```python
async def upload_to_s3(file_content: bytes, key: str) -> None:
    """Upload file to S3 asynchronously."""
    # Use async AWS SDK
    pass

async def process_diagram(diagram_id: str) -> dict:
    """Process diagram with async operations."""
    content = await fetch_from_storage(diagram_id)
    result = await analyze_content(content)
    await save_result(diagram_id, result)
    return result
```

## Code Organization Within Files

Order within a file:

1. Module docstring
2. Imports
3. Constants
4. Exception classes
5. Main classes/functions
6. Helper functions (private)

```python
"""
Diagram service module.

Provides business logic for diagram analysis.
"""

import os
from typing import List

from app.core.domain.entities.diagram import Diagram

MAX_RETRIES = 3

class DiagramProcessingError(Exception):
    """Raised when diagram processing fails."""

class DiagramService:
    """Main service for diagram operations."""
    
    def analyze(self, diagram: Diagram) -> dict:
        """Public method."""
        return self._process(diagram)
    
    def _process(self, diagram: Diagram) -> dict:
        """Private helper method."""
        pass
```
