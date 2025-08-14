# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that wraps the Temporal CLI to expose workflow management functionality. The server uses FastMCP and provides JSON-formatted responses for all Temporal workflow operations.

## Architecture

- **Core module** (`src/temporal_cli_mcp/core.py`): Contains the FastMCP server instance and `run_temporal_command()` function that executes temporal CLI commands with global env/JSON flags
- **Workflow tools** (`src/temporal_cli_mcp/workflow/`): Individual modules for each workflow operation (list, describe, start, signal, query, cancel, terminate, history)
- **Tool registration**: All workflow tools are automatically registered via imports in `__init__.py`

## Development Commands

### Running the MCP Server
```bash
# Development mode (via uv)
uv run python -m temporal_cli_mcp --env staging

# Production mode (if installed)
temporal-cli-mcp --env prod
```

### Testing
```bash
# Run test script
python test_mcp.py

# Test with environment flag
python test_env_flag.py
```

### Dependencies
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package>
```

## Key Implementation Details

- All temporal CLI commands are executed with `--env <env>`, `-o json`, and `--time-format iso` flags automatically
- The `_TEMPORAL_GLOBAL_PREFIX` variable stores global flags (like `--env`) that are prepended to all commands
- Tool functions are async and use the `@mcp.tool()` decorator for automatic registration
- Error handling wraps subprocess exceptions and returns structured JSON responses
- Only the `workflow` command group from Temporal CLI is exposed

## Configuration

The MCP server accepts an `--env` argument to specify which Temporal CLI environment to use. This gets stored globally and applied to all temporal commands.

Example MCP client configuration:
```json
{
  "mcpServers": {
    "temporal-cli": {
      "command": "uv",
      "args": ["run", "python", "-m", "temporal_cli_mcp", "--env", "prod"],
      "cwd": "/path/to/temporal-cli-mcp"
    }
  }
}
```

## Best Practices

### Workflow Query Optimization

When working with workflow listings, always use `count_workflows` before `list_workflows` to:

- **Optimize token usage**: Avoid large responses when dealing with many workflows
- **Provide context**: Get scope understanding before detailed queries  
- **Cost efficiency**: Reduce unnecessary API calls and token consumption
- **Informed decisions**: Choose appropriate limits and filters based on counts

**Recommended workflow:**
```python
# First, get the count to understand scope
count_result = await count_workflows(query="WorkflowType = 'OnboardingFlow'")
print(f"Found {count_result['count']} matching workflows")

# Then list with appropriate limit based on count
if count_result['count'] > 50:
    # Use smaller limit for large result sets
    workflows = await list_workflows(query="WorkflowType = 'OnboardingFlow'", limit=10)
else:
    # Can safely list all for smaller sets
    workflows = await list_workflows(query="WorkflowType = 'OnboardingFlow'", limit=count_result['count'])
```

### Query Building

- Use `build_workflow_query` for complex filtering requirements
- Validate queries with `validate_workflow_query` before execution
- See `get_query_examples` for common query patterns

## Prerequisites

- Temporal CLI must be installed and available in PATH
- Temporal CLI environments must be configured in `~/.config/temporalio/temporal.yaml`
- Python 3.11+