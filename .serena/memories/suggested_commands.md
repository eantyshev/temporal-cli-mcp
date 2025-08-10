# Suggested Commands

## Development Commands

### Running the MCP Server
```bash
# Development mode (recommended)
uv run python -m temporal_cli_mcp --env staging

# Production mode (if installed)
temporal-cli-mcp --env prod
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package>

# Remove dependency
uv remove <package>

# Update dependencies
uv lock
```

### Testing
```bash
# Run the MCP server test
python test_mcp.py

# Test with environment flag
python test_env_flag.py

# Manual testing via direct module execution
uv run python -m temporal_cli_mcp
```

### Building and Installation
```bash
# Build the package
uv build

# Install locally for development
uv pip install -e .
```

## Temporal CLI Commands (External)
```bash
# Setup Temporal CLI environment
temporal --env <env-name> workflow <args>

# Check available environments
cat ~/.config/temporalio/temporal.yaml

# Test Temporal CLI connectivity
temporal --env <env-name> workflow list --limit 1
```

## System Commands
```bash
# Standard Linux commands available
ls, cd, grep, find, cat, head, tail, etc.

# Git operations
git status, git add, git commit, git push, etc.
```