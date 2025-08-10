# New Development Patterns

## Updated Architecture Pattern

### Using the New Components

When adding new workflow tools, follow this pattern:

```python
# In workflow/<command>.py
from typing import Dict, Any
from ..models import WorkflowCommandRequest  # Create specific model
from ..base import AsyncCommandExecutor
from ..command_builder import TemporalCommandBuilder
from ..config import config
from ..exceptions import ValidationError
from ..core import mcp

@mcp.tool()
async def new_workflow_command(**kwargs) -> Dict[str, Any]:
    try:
        # 1. Validate input
        request = WorkflowCommandRequest(**kwargs)
        
        # 2. Create executor and builder
        executor = AsyncCommandExecutor()
        builder = TemporalCommandBuilder(env=config.env)
        
        # 3. Build and execute command
        workflow_args = builder.build_workflow_command(request)
        cmd = builder.build_full_command(workflow_args)
        result = await executor.execute(cmd)
        
        # 4. Handle result
        if not result["success"]:
            raise Exception(f"Command failed: {result['stderr']}")
        
        return result
        
    except Exception as e:
        if "ValidationError" in str(type(e)):
            raise ValidationError(f"Invalid input: {e}")
        raise
```

### Key Principles

1. **Input Validation First**: Always validate inputs with Pydantic models
2. **Use Async Execution**: Never use synchronous subprocess calls
3. **Structured Error Handling**: Use custom exceptions, not generic ones
4. **Command Builder**: Use TemporalCommandBuilder for all command construction
5. **Logging**: Let the base classes handle logging automatically

### File Organization

```
src/temporal_cli_mcp/
├── exceptions.py       # Custom exception hierarchy
├── models.py          # Pydantic validation models
├── config.py          # Configuration management
├── command_builder.py # Command construction
├── base.py           # Abstract base classes
├── core.py           # MCP server and legacy compatibility
└── workflow/         # Individual command implementations
    ├── __init__.py   # Tool registration
    ├── list.py       # Updated example
    ├── describe.py   # To be updated
    └── ...
```

### Error Handling Pattern

```python
try:
    # Validation and execution
    pass
except ValidationError:
    # Re-raise validation errors as-is
    raise
except CommandExecutionError as e:
    # Handle command-specific errors
    logger.error(f"Command failed: {e}")
    raise
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
    raise
```

### Testing Pattern

```python
# For future unit tests
import pytest
from unittest.mock import AsyncMock, patch

async def test_workflow_command():
    with patch('temporal_cli_mcp.base.AsyncCommandExecutor') as mock_executor:
        mock_executor.return_value.execute = AsyncMock(return_value={
            "success": True,
            "data": {"workflow_id": "test"}
        })
        
        result = await workflow_command(param="value")
        assert result["success"] is True
```