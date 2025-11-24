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

The project includes a comprehensive test infrastructure following kubectl-mcp patterns. Tests can be run in two modes:

**Mock Mode (Recommended for Development):**
```bash
# Run all tests safely without Temporal CLI
task test

# Run specific test categories
task test:core          # Core MCP functionality tests
task test:mock          # Explicit mock mode
task quick              # Quick single test
task quick:all          # Quick core test suite

# Generate test reports
task test:coverage      # Run with coverage report
task test:report        # Generate HTML report
```

**Integration Mode (Requires Temporal CLI Access):**
```bash
# Test against staging environment
task test:staging

# Test against production environment (use carefully)
task test:prod

# Validate Temporal CLI setup
task validate:temporal
```

**Test Development:**
```bash
# Install test dependencies
task test:install-deps

# Run tests in watch mode (reruns on changes)
task test:watch

# Run a specific test
task test:single -- tests/test_mcp_core.py::TestTemporalMCPCore::test_list_tools

# Demo test infrastructure
task demo:mcp           # Demo MCP client simulator
task demo:utils         # Demo test utilities
```

**Environment Variables:**
```bash
# Enable mock mode (no Temporal CLI calls)
export TEMPORAL_MCP_TEST_MOCK_MODE=1

# Set test environment
export TEMPORAL_TEST_ENV=staging

# Set test timeout
export TEMPORAL_TEST_TIMEOUT=30

# Enable debug logging
export TEMPORAL_TEST_LOG_LEVEL=DEBUG
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

### Workflow History Filtering

**Problem**: Workflow histories can be very large (45KB+ for 214 events), consuming significant tokens and making debugging difficult.

**Solution**: Use `get_workflow_history` filtering parameters to reduce response size by 20x or more.

**Key Filtering Parameters:**

1. **Event Type Filtering** - Focus on relevant events only:
   ```python
   # Get only failures for debugging
   get_workflow_history(
       workflow_id="megaflow-xyz",
       event_types=["WORKFLOW_TASK_FAILED", "ACTIVITY_TASK_FAILED", "CHILD_WORKFLOW_EXECUTION_FAILED"]
   )
   
   # Exclude verbose events
   get_workflow_history(
       workflow_id="megaflow-xyz",
       exclude_event_types=["TIMER_FIRED", "TIMER_STARTED", "MARKER_RECORDED"]
   )
   ```

2. **Smart Presets** - Common debugging scenarios:
   ```python
   # Last failure + 10 events before it (perfect for debugging non-deterministic errors)
   get_workflow_history(workflow_id="megaflow-xyz", preset="last_failure_context")
   
   # Only key state transitions
   get_workflow_history(workflow_id="megaflow-xyz", preset="summary")
   
   # All WORKFLOW_TASK_FAILED events (find resets)
   get_workflow_history(workflow_id="megaflow-xyz", preset="resets")
   
   # Exclude verbose events (timers, markers)
   get_workflow_history(workflow_id="megaflow-xyz", preset="critical_path")
   ```

3. **Pagination & Ordering** - Get recent events first:
   ```python
   # Last 30 events, most recent first (99% of debugging looks at recent activity)
   get_workflow_history(
       workflow_id="megaflow-xyz",
       reverse=True,
       limit=30
   )
   ```

4. **Field Projection** - Reduce payload size:
   ```python
   # Minimal: Only eventId, eventType, eventTime
   get_workflow_history(workflow_id="megaflow-xyz", fields="minimal")
   
   # Standard: Add failure messages and key identifiers (recommended for debugging)
   get_workflow_history(workflow_id="megaflow-xyz", fields="standard")
   
   # Full: Everything including payloads (default, largest response)
   get_workflow_history(workflow_id="megaflow-xyz", fields="full")
   ```

**Most Common Use Case** (reduces 45KB to ~2KB):
```python
# Perfect for debugging: recent events, failures, no payloads
get_workflow_history(
    workflow_id="megaflow-xyz",
    reverse=True,
    limit=30,
    event_types=["WORKFLOW_TASK_FAILED", "WORKFLOW_TASK_COMPLETED", "ACTIVITY_TASK_FAILED"],
    fields="standard"
)
```

**Combining Filters** - All filters work together:
```python
# Get last 20 critical events without timers
get_workflow_history(
    workflow_id="megaflow-xyz",
    exclude_event_types=["TIMER_FIRED", "TIMER_STARTED"],
    reverse=True,
    limit=20,
    fields="standard"
)
```

**Important Notes:**
- All filtering is **post-processing** after fetching from Temporal CLI
- Filtering doesn't improve fetch performance but dramatically reduces token usage
- `preset` parameter overrides `event_types` and `exclude_event_types` (but not `fields`, `limit`, `reverse`)
- Without filtering, full history is returned for backwards compatibility

**Handling Timeouts for Large Histories:**

If you get "context deadline exceeded" errors for very large workflow histories:

```python
# Increase timeout for large histories (default is 60s)
get_workflow_history(
    workflow_id="megaflow-xyz",
    timeout_seconds=120,  # 2 minutes
    preset="critical_path",
    fields="standard"
)
```

**Timeout Guidelines:**
- **Default (60s)**: Suitable for most workflows (<500 events)
- **120s**: For large workflows (500-2000 events)
- **180s+**: For very large workflows (2000+ events)
- Combine with filtering presets to reduce both fetch time and response size

### Query Building

- Use `build_workflow_query` for complex filtering requirements
- Validate queries with `validate_workflow_query` before execution
- See `get_query_examples` for common query patterns

## Testing Architecture

The project uses a comprehensive testing strategy adapted from kubectl-mcp-server patterns:

### Test Components

- **MCP Client Simulator** (`tests/mcp_client_simulator.py`): Full MCP protocol simulation for end-to-end testing
- **Test Utilities** (`tests/test_utils.py`): Environment setup, validation functions, and mock data generators
- **Test Runner** (`tests/run_tests.py`): Test execution, dependency checking, and reporting
- **Core Tests** (`tests/test_mcp_core.py`): MCP protocol compliance and workflow operation tests

### Test Modes

1. **Mock Mode**: Safe offline testing with simulated responses (default)
2. **Integration Mode**: Real Temporal CLI integration testing (requires environment access)

### Running Tests

Always run tests in mock mode during development to avoid affecting real environments:

```bash
# Recommended: Run all tests in mock mode
task test

# Quick development workflow
task quick              # Single test
task quick:all          # Core test suite
task test:watch         # Watch mode for TDD
```

For integration testing with real Temporal CLI (use carefully):

```bash
task validate:temporal  # Check Temporal CLI setup first
task test:staging       # Test against staging
```

### CI/CD Integration

```bash
# Simulate CI pipeline
task ci                 # Basic CI simulation
task ci:full            # Full CI with coverage and reports
```

## Prerequisites

- Temporal CLI must be installed and available in PATH
- Temporal CLI environments must be configured in `~/.config/temporalio/temporal.yaml`
- Python 3.11+
- Task (go-task.github.io) for running development commands