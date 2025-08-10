# Code Style and Conventions

## Code Style
- **Type Hints**: Extensive use of type hints throughout the codebase
  - Functions use `-> Dict[str, Any]` return types
  - Parameters use `Optional[str]` for nullable strings
  - Import `from typing import Any, Dict, List, Optional`

- **Function Signatures**: Async functions with keyword-only arguments
  ```python
  async def run_temporal_command(args: List[str], *, output: str = "json") -> Dict[str, Any]:
  ```

- **Docstrings**: Simple docstrings with bullet points for key information
  ```python
  """Execute a temporal CLI command and return the result with optional JSON parsing.

  - Only the `workflow` command group is intended to be used by tools in this MCP.
  - By default, forces JSON output via global `-o json` for easy parsing.
  - Respects a global `--env <value>` if provided to this MCP process.
  """
  ```

## Naming Conventions
- **Variables**: snake_case (e.g., `global_flags`, `content_length`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `_TEMPORAL_GLOBAL_PREFIX`)
- **Functions**: snake_case (e.g., `run_temporal_command`, `list_workflows`)
- **Private variables**: Leading underscore (e.g., `_TEMPORAL_GLOBAL_PREFIX`)

## Import Style
- Standard library imports first
- Third-party imports second
- Relative imports last
```python
import argparse
import json
import subprocess
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .core import mcp, run_temporal_command
```

## Decorator Usage
- MCP tools use `@mcp.tool()` decorator for automatic registration
- All tool functions are async

## Error Handling
- Use try/except blocks for subprocess operations
- Return structured dictionaries with success/failure status
- Include command details in error responses