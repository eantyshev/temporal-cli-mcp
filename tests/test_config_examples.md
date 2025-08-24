# Test Configuration Examples

This document provides examples of how to configure and run tests for temporal-cli-mcp in different scenarios.

## Environment Variables

### Basic Test Configuration

```bash
# Mock mode (no Temporal CLI calls) - RECOMMENDED for development
export TEMPORAL_MCP_TEST_MOCK_MODE=1

# Test environment selection
export TEMPORAL_TEST_ENV=staging

# Test timeouts
export TEMPORAL_TEST_TIMEOUT=30

# Logging configuration
export TEMPORAL_TEST_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Development Environment

```bash
# .env file for development
TEMPORAL_MCP_TEST_MOCK_MODE=1
TEMPORAL_TEST_ENV=staging
TEMPORAL_TEST_TIMEOUT=30
TEMPORAL_TEST_LOG_LEVEL=DEBUG
TEMPORAL_TEST_RETRIES=3
```

### CI/CD Environment

```bash
# GitHub Actions / CI environment
TEMPORAL_MCP_TEST_MOCK_MODE=1
TEMPORAL_TEST_ENV=staging
TEMPORAL_TEST_TIMEOUT=60
TEMPORAL_TEST_LOG_LEVEL=INFO
```

## Task Examples

### Basic Development Workflow

```bash
# Start development session
task setup                          # Set up environment
task validate:env                   # Validate setup
task test                           # Run all tests (mock mode)

# Iterative development
task quick                          # Quick single test
task test:core                      # Core functionality tests
task test:watch                     # Watch mode for TDD

# Before committing
task test:coverage                  # Run with coverage
task ci                            # Simulate CI pipeline
```

### Integration Testing

```bash
# Validate Temporal CLI access first
task validate:temporal

# Run integration tests
task test:staging                   # Test against staging
task test:prod                      # Test against production (careful!)

# Specific environment testing
TEMPORAL_TEST_ENV=my-env task test:staging
```

### Debugging and Development

```bash
# Run with debug logging
TEMPORAL_TEST_LOG_LEVEL=DEBUG task test:core

# Run a specific test
task test:single -- tests/test_mcp_core.py::TestTemporalMCPCore::test_list_tools

# Demo the infrastructure
task demo:mcp                       # Demo MCP client simulator
task demo:utils                     # Demo test utilities

# Watch mode for TDD
task test:watch
```

### Reporting and Coverage

```bash
# Generate HTML test report
task test:report

# Run with coverage report
task test:coverage

# Full CI simulation with reports
task ci:full

# Clean up test artifacts
task test:clean
```

## Pytest Direct Usage

If you prefer using pytest directly instead of task commands:

### Mock Mode (Recommended)

```bash
# Basic test run
TEMPORAL_MCP_TEST_MOCK_MODE=1 uv run pytest tests/ -v

# With coverage
TEMPORAL_MCP_TEST_MOCK_MODE=1 uv run pytest tests/ --cov=src/temporal_cli_mcp --cov-report=html

# Specific test
TEMPORAL_MCP_TEST_MOCK_MODE=1 uv run pytest tests/test_mcp_core.py::TestTemporalMCPCore::test_list_tools -v

# Watch mode
TEMPORAL_MCP_TEST_MOCK_MODE=1 uv run ptw tests/ -- -v
```

### Integration Mode

```bash
# Staging environment
TEMPORAL_TEST_ENV=staging uv run pytest tests/ -v

# Production environment
TEMPORAL_TEST_ENV=prod uv run pytest tests/ -v

# Skip integration tests (run only unit/mock tests)
uv run pytest tests/ -v -m "not integration"
```

## Docker Environment

### Running Tests in Docker

```dockerfile
# Dockerfile.test
FROM python:3.11

WORKDIR /app
COPY . .

# Install dependencies
RUN pip install uv
RUN uv sync

# Install test dependencies
RUN uv add --dev pytest pytest-asyncio pytest-cov

# Set test environment
ENV TEMPORAL_MCP_TEST_MOCK_MODE=1
ENV TEMPORAL_TEST_LOG_LEVEL=INFO

# Run tests
CMD ["uv", "run", "pytest", "tests/", "-v"]
```

```bash
# Build and run test container
docker build -f Dockerfile.test -t temporal-mcp-test .
docker run --rm temporal-mcp-test
```

## GitHub Actions Configuration

### Basic CI Workflow

```yaml
# .github/workflows/test.yml
name: Test Temporal CLI MCP

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
        test-mode: [mock]

    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
          uv add --dev pytest pytest-asyncio pytest-cov pytest-html
      
      - name: Run tests
        env:
          TEMPORAL_MCP_TEST_MOCK_MODE: 1
          TEMPORAL_TEST_LOG_LEVEL: INFO
        run: |
          uv run pytest tests/ --cov=src/temporal_cli_mcp --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Advanced CI with Multiple Environments

```yaml
# .github/workflows/test-advanced.yml
name: Advanced Testing

on:
  push:
    branches: [ main ]

jobs:
  mock-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup and test
        run: |
          pip install uv
          uv sync
          uv add --dev pytest pytest-asyncio pytest-cov
          TEMPORAL_MCP_TEST_MOCK_MODE=1 uv run pytest tests/ -v

  integration-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Install Temporal CLI
        run: |
          # Install Temporal CLI for integration tests
          curl -sSf https://temporal.download/cli.sh | sh
      - name: Setup and test
        env:
          TEMPORAL_TEST_ENV: staging
          # Add Temporal Cloud credentials as secrets
        run: |
          pip install uv
          uv sync
          uv add --dev pytest pytest-asyncio
          uv run pytest tests/ -v -m "not slow"
```

## VS Code Configuration

### Launch Configuration

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run Tests (Mock)",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal",
            "env": {
                "TEMPORAL_MCP_TEST_MOCK_MODE": "1",
                "TEMPORAL_TEST_LOG_LEVEL": "DEBUG"
            }
        },
        {
            "name": "Run Single Test",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["${file}", "-v"],
            "console": "integratedTerminal",
            "env": {
                "TEMPORAL_MCP_TEST_MOCK_MODE": "1"
            }
        }
    ]
}
```

### Settings

```json
// .vscode/settings.json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests/"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestPath": "uv run pytest",
    "python.envFile": "${workspaceFolder}/.env.test"
}
```

### Environment File

```bash
# .env.test
TEMPORAL_MCP_TEST_MOCK_MODE=1
TEMPORAL_TEST_ENV=staging
TEMPORAL_TEST_LOG_LEVEL=DEBUG
TEMPORAL_TEST_TIMEOUT=30
```

## Common Testing Patterns

### Test-Driven Development

```bash
# 1. Start watch mode
task test:watch

# 2. Write failing test
# 3. Make it pass
# 4. Refactor
# 5. Repeat
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Running pre-commit tests..."
TEMPORAL_MCP_TEST_MOCK_MODE=1 uv run pytest tests/ --tb=short
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
echo "All tests passed."
```

### Development Environment Setup

```bash
# Initial setup
git clone <repo>
cd temporal-cli-mcp
task setup                      # Install everything
task validate:env              # Verify setup
task test                       # Run tests
task demo:mcp                   # Demo the infrastructure

# Daily development
task test:watch                 # Start TDD session
# ... develop ...
task ci                         # Pre-commit check
```

This configuration covers most development and testing scenarios for the temporal-cli-mcp project.