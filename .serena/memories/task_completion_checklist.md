# Task Completion Checklist

## When a Development Task is Completed

### 1. Code Quality Checks
Since this project uses uv but doesn't have explicit linting/formatting tools configured in pyproject.toml:

```bash
# Check Python syntax
python -m py_compile src/temporal_cli_mcp/*.py

# Manual code review for:
# - Type hints consistency
# - Docstring format
# - Import organization
# - Error handling patterns
```

### 2. Testing
```bash
# Run the MCP server test
python test_mcp.py

# Test with environment flag (if applicable)
python test_env_flag.py

# Manual functional testing
uv run python -m temporal_cli_mcp --env <test-env>
```

### 3. Dependencies
```bash
# Ensure dependencies are locked
uv lock

# Verify installation works
uv sync
```

### 4. Documentation
- Update README.md if new tools are added
- Update CLAUDE.md if development commands change
- Ensure docstrings are present for new functions

### 5. Integration Testing
```bash
# Test MCP server startup
uv run python -m temporal_cli_mcp --help

# Test with actual Temporal CLI (if available)
# temporal --env <test-env> workflow list --limit 1
```

## Notes
- No automated linting/formatting tools are configured
- No unit test framework is present (only integration tests)
- Manual code review is essential
- Ensure Temporal CLI compatibility is maintained