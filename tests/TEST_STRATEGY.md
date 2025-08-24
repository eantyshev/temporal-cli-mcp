# Temporal CLI MCP - Comprehensive Testing Strategy

This document outlines a systematic approach to test the temporal-cli-mcp's MCP integration across all workflow management features. Based on kubectl-mcp-server testing patterns and adapted for Temporal workflow operations.

## Testing Objectives

1. Validate that all workflow tools work correctly through the MCP protocol interface
2. Ensure proper error handling and response formatting
3. Test both synchronous and asynchronous operations
4. Verify correct behavior under various Temporal environment states
5. Test query building and validation functionality
6. Ensure proper environment isolation and configuration

## Test Environment Setup

### Prerequisites

- Temporal CLI installed and configured with environments
- Python 3.11+ with pytest and pytest-asyncio
- Access to Temporal Cloud environments (staging/prod)
- MCP client simulator for request generation

### Environment Management

- Use dedicated Temporal environments for testing (staging recommended)
- Support mock mode for offline testing and CI
- Environment variables for configuration and test control
- Proper cleanup and isolation between test runs

```python
# Environment setup example
def setup_temporal_test_environment(env="staging"):
    """Setup test environment with proper configuration"""
    if not check_temporal_cli_available():
        raise RuntimeError("Temporal CLI not found")
    
    if not validate_temporal_env(env):
        raise RuntimeError(f"Cannot access Temporal environment: {env}")
    
    return env
```

## Test Categories

### 1. Core Workflow Operations Tests

Test the fundamental workflow management capabilities:

- **Workflow Listing**: Basic listing, query filtering, pagination
- **Workflow Description**: Detailed workflow information retrieval  
- **Workflow History**: Event history with payload decoding
- **Workflow Counting**: Count operations with query support
- **Workflow Control**: Start, signal, query, cancel, terminate, reset
- **Workflow Monitoring**: Stack traces, failure analysis

### 2. Query Builder Integration Tests

Test the comprehensive query building and validation system:

- **Structured Query Building**: Field filters, IN clauses, time ranges
- **Query Validation**: Syntax checking, field validation, operator support
- **Query Execution**: End-to-end query building and execution
- **Fallback Patterns**: WorkflowType to WorkflowId prefix fallback
- **Complex Queries**: Multi-condition, nested logical operators

### 3. Error Handling Tests

Test comprehensive error scenarios:

- **CLI Unavailable**: Temporal CLI not found or not working
- **Environment Issues**: Invalid environments, connection failures
- **Invalid Parameters**: Malformed workflow IDs, invalid queries
- **Timeout Scenarios**: Long-running operations, network issues
- **Response Parsing**: Malformed JSON, unexpected output formats

### 4. Performance and Load Tests

Test system behavior under various loads:

- **Concurrent Requests**: Multiple simultaneous MCP requests
- **Large Result Sets**: Handling thousands of workflow results
- **Memory Efficiency**: Large payloads, payload decoding
- **Timeout Handling**: Long-running queries and operations

### 5. Protocol Compliance Tests

Test MCP protocol adherence:

- **Protocol Initialization**: Proper MCP handshake and setup
- **Tool Registration**: All tools properly registered and described
- **Response Formatting**: Correct MCP response structure
- **Error Propagation**: Proper MCP error handling and reporting

## Test Structure

```python
class TestTemporalMCPCore:
    """Test core Temporal MCP functionality through MCP protocol"""
    
    @pytest.fixture(scope="class")
    def mcp_client(self):
        """Fixture to create and manage MCP client"""
        with temporal_mcp_client(env="staging") as client:
            yield client
    
    @pytest.fixture
    def test_environment(self):
        """Setup test environment for each test"""
        with temporal_test_context(env="staging") as env:
            yield env
    
    def test_list_tools(self, mcp_client):
        """Test that all expected tools are available"""
        response = mcp_client.list_tools()
        
        # Validate MCP response format
        is_valid, error = validate_mcp_response(response)
        assert is_valid, f"Invalid MCP response: {error}"
        
        # Check for required workflow tools
        tools = response["result"]["tools"]
        expected_tools = [
            "list_workflows", "describe_workflow", "get_workflow_history",
            "count_workflows", "start_workflow", "signal_workflow", 
            "query_workflow", "cancel_workflow", "terminate_workflow",
            "reset_workflow", "trace_workflow", "build_workflow_query"
        ]
        
        for tool_name in expected_tools:
            assert_tool_exists(tools, tool_name)
    
    def test_workflow_operations(self, mcp_client):
        """Test basic workflow operations"""
        # Test workflow listing
        response = mcp_client.call_workflow_tool("list_workflows", limit=5)
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid workflow response: {error}"
        
        # Test workflow counting  
        response = mcp_client.call_workflow_tool("count_workflows")
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid count response: {error}"
```

## MCP Client Simulator

Comprehensive MCP client for protocol-level testing:

```python
class TemporalMCPClientSimulator:
    """Simulate an MCP client for testing Temporal workflow operations"""
    
    def __init__(self, env="staging", timeout=30):
        """Initialize with Temporal environment configuration"""
        self.env = env
        self.timeout = timeout
        
    def call_workflow_tool(self, tool_name: str, **kwargs):
        """Call temporal workflow tools through MCP protocol"""
        return self.call_tool(tool_name, kwargs)
    
    def test_workflow_listing(self, query=None, limit=10):
        """Test workflow listing with optional query"""
        args = {"limit": limit}
        if query:
            args["query"] = query
        return self.call_workflow_tool("list_workflows", **args)
```

## Test Data Generation

Utilities for generating consistent test data:

```python
def generate_test_workflow_query(workflow_type=None, status=None):
    """Generate valid test workflow queries"""
    conditions = []
    if workflow_type:
        conditions.append(f"WorkflowType = '{workflow_type}'")
    if status:
        conditions.append(f"ExecutionStatus = '{status}'")
    return " AND ".join(conditions)

def generate_test_structured_query():
    """Generate structured query for query builder testing"""
    return {
        "field_filters": [
            {"field": "WorkflowType", "operator": "=", "value": "TestWorkflow"}
        ],
        "logical_operator": "AND"
    }
```

## Validation Utilities

Functions to validate responses and state:

```python
def validate_mcp_response(response, expected_schema=None):
    """Validate MCP protocol compliance"""
    # Check jsonrpc version, id, result/error structure
    
def validate_temporal_workflow_response(response):
    """Validate Temporal workflow command response"""
    # Check for success field, data structure, temporal-specific fields

def validate_query_syntax(query_string):
    """Validate Temporal query syntax"""
    # Check for balanced quotes, valid operators, supported fields
```

## Mock Mode Support

Comprehensive mock mode for offline testing:

```python
# Environment variable control
MOCK_MODE = os.environ.get("TEMPORAL_MCP_TEST_MOCK_MODE", "0") == "1"

# Mock responses for different operations
MOCK_RESPONSES = {
    "list_workflows": generate_mock_workflow_list(),
    "describe_workflow": generate_mock_workflow_description(),
    "count_workflows": {"success": True, "data": {"count": 42}}
}
```

## Test Execution Plan

### Phase 1: Infrastructure Setup (Day 1)
- MCP client simulator implementation ✓
- Test utilities and validation functions ✓
- Mock mode support ✓
- Test runner and configuration ✓

### Phase 2: Core Functionality Tests (Days 2-3)
- Basic workflow operations (list, describe, count)
- Workflow control operations (start, signal, cancel, etc.)
- Error handling and edge cases
- Response validation and formatting

### Phase 3: Query Builder Tests (Day 4)
- Structured query building and validation
- Query execution integration
- Fallback pattern testing
- Complex query scenarios

### Phase 4: Advanced Features (Day 5)
- Performance and load testing
- Concurrent request handling
- Large dataset processing
- Timeout and reliability testing

### Phase 5: CI Integration (Day 6)
- GitHub Actions workflow setup
- Automated testing on PRs
- Test coverage reporting
- Documentation and examples

## Test Coverage Goals

- **Protocol Compliance**: 100% MCP protocol adherence
- **Tool Coverage**: All workflow tools tested
- **Error Scenarios**: Comprehensive error handling
- **Query Features**: Complete query builder validation
- **Performance**: Load and stress testing
- **Documentation**: Clear examples and guides

## Running Tests

### Basic Usage

```bash
# Run all tests
./tests/run_tests.py

# Run with specific environment
./tests/run_tests.py --env prod

# Run in mock mode
./tests/run_tests.py --mock

# Run specific test module
./tests/run_tests.py --module test_workflow_operations

# Generate HTML report
./tests/run_tests.py --report

# Install test dependencies
./tests/run_tests.py --install-deps
```

### Environment Variables

```bash
# Test configuration
export TEMPORAL_TEST_ENV=staging
export TEMPORAL_MCP_TEST_MOCK_MODE=1
export TEMPORAL_TEST_TIMEOUT=30
export TEMPORAL_TEST_LOG_LEVEL=DEBUG

# Run tests
./tests/run_tests.py
```

## Continuous Integration

The testing strategy integrates with CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Test Temporal CLI MCP
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
        test-mode: [mock, staging]
    
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: ./tests/run_tests.py --install-deps
      
      - name: Run tests
        run: ./tests/run_tests.py --${{ matrix.test-mode }} --report
      
      - name: Upload test results
        uses: actions/upload-artifact@v4
        with:
          name: test-results-${{ matrix.python-version }}-${{ matrix.test-mode }}
          path: test_reports/
```

## Benefits of This Testing Strategy

1. **Comprehensive Coverage**: Tests all aspects of workflow management
2. **Protocol Compliance**: Ensures proper MCP integration
3. **Environment Isolation**: Safe testing without affecting production
4. **Mock Mode**: Enables offline testing and CI integration
5. **Performance Testing**: Validates behavior under load
6. **Clear Documentation**: Easy to understand and extend
7. **Automated Execution**: Integrates with CI/CD pipelines
8. **Error Resilience**: Comprehensive error scenario testing

This testing strategy provides a solid foundation for reliable, maintainable testing of the temporal-cli-mcp server, ensuring both functionality and protocol compliance.