# Project Overview

## Purpose
This is a Model Context Protocol (MCP) server that wraps the Temporal CLI for automation of workflow inspection and one-off operations. It focuses exclusively on the `workflow` command group and outputs JSON for easy parsing.

## Tech Stack
- **Language**: Python 3.11+
- **Package Manager**: uv (ultra-fast Python package manager)
- **Framework**: FastMCP (>=0.2.0) for MCP server implementation
- **CLI Tool**: Temporal CLI (must be installed separately and available in PATH)

## Key Features
- Wraps only the Temporal workflow commands (list, describe, start, signal, query, cancel, terminate, show/history)
- All commands executed with `-o json --time-format iso` for consistent JSON output
- Environment-aware: uses `--env` flag to select Temporal CLI environments
- Returns structured JSON responses with parsed data and raw CLI output

## Dependencies
- fastmcp>=0.2.0 (only dependency in pyproject.toml)
- Temporal CLI (external requirement, must be installed separately)
- Python 3.11+ required

## Project Structure
```
src/temporal_cli_mcp/
├── __init__.py
├── __main__.py          # Entry point
├── core.py              # FastMCP server instance and command execution
├── workflow_tools.py    # All workflow tool implementations
└── workflow/            # Individual workflow command modules
    ├── __init__.py      # Tool registration aggregator
    ├── list.py
    ├── describe.py
    ├── start.py
    ├── signal.py
    ├── query.py
    ├── cancel.py
    ├── terminate.py
    └── history.py
```