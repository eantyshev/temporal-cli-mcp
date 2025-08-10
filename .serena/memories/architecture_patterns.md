# Architecture and Design Patterns

## Core Architecture Patterns

### 1. FastMCP Server Pattern
- Single global `mcp` instance in `core.py`
- Tool registration via `@mcp.tool()` decorators
- Automatic tool discovery through imports

### 2. Command Execution Pattern
```python
# Centralized command execution with global flags
async def run_temporal_command(args: List[str], *, output: str = "json") -> Dict[str, Any]
```
- Global prefix handling (`_TEMPORAL_GLOBAL_PREFIX`)
- Consistent JSON output formatting
- Structured error responses

### 3. Tool Organization Pattern
- Individual tool modules in `workflow/` directory
- Tool registration aggregator in `workflow/__init__.py`
- Import-based registration (side effects on import)

### 4. Response Structure Pattern
All tools return consistent structure:
```python
{
    "success": bool,
    "returncode": int,
    "stdout": str,
    "stderr": str, 
    "cmd": List[str],
    "data": Dict[str, Any] | None  # Parsed JSON if available
}
```

## Key Design Decisions

### Environment Handling
- Global `--env` flag stored in `_TEMPORAL_GLOBAL_PREFIX`
- Applied to all temporal CLI calls automatically
- No per-tool environment configuration

### JSON-First Approach
- All temporal commands executed with `-o json --time-format iso`
- Parsing attempted, fallback to raw output on failure
- Consistent timestamp formatting

### Error Handling Strategy
- Subprocess exceptions caught and converted to response dictionaries
- FileNotFoundError handled specifically for missing temporal CLI
- No tool-level exceptions, always return response dict

### Tool Registration
- Declarative via decorators
- Automatic discovery through module imports
- No explicit registration calls needed