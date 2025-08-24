#!/usr/bin/env python3
"""
Test utilities for temporal-cli-mcp testing.
Provides functions for test setup, validation, and data generation.
Adapted from kubectl-mcp-server test patterns.
"""

import os
import time
import json
import uuid
import logging
import subprocess
from typing import Dict, List, Any, Tuple, Optional, Union, Callable
from contextlib import contextmanager
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Check if we're running in mock mode
MOCK_MODE = os.environ.get("TEMPORAL_MCP_TEST_MOCK_MODE", "0") == "1"


def setup_temporal_test_environment(env: str = "staging", 
                                   max_retries: int = 3,
                                   wait_time: int = 2) -> bool:
    """
    Setup and validate Temporal test environment.
    
    Args:
        env: Temporal environment to test
        max_retries: Maximum number of retry attempts
        wait_time: Time to wait between retries (seconds)
        
    Returns:
        True if environment is ready, False otherwise
    """
    if MOCK_MODE:
        logger.info(f"[MOCK] Temporal environment '{env}' is ready")
        return True
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Checking Temporal environment '{env}' (attempt {attempt+1}/{max_retries})")
            
            # Test temporal CLI availability
            result = subprocess.run(
                ["temporal", "--env", env, "workflow", "list", "--limit", "1"],
                capture_output=True, check=True, text=True, timeout=10
            )
            
            logger.info(f"Temporal environment '{env}' is ready")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Temporal environment check failed: {e.stderr}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to validate Temporal environment after {max_retries} attempts")
                return False
        except FileNotFoundError:
            logger.error("Temporal CLI not found. Please install Temporal CLI.")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("Temporal CLI command timed out")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
    
    return False


@contextmanager
def temporal_test_context(env: str = "staging"):
    """
    Context manager for Temporal test environment setup and cleanup.
    
    Args:
        env: Temporal environment to use
        
    Yields:
        Environment name if successful
        
    Raises:
        RuntimeError: If environment setup fails
    """
    logger.info(f"Setting up Temporal test context for environment: {env}")
    
    # Validate environment is available
    if not MOCK_MODE and not setup_temporal_test_environment(env):
        raise RuntimeError(f"Failed to setup Temporal test environment: {env}")
    
    try:
        yield env
    finally:
        logger.info(f"Cleaning up Temporal test context for environment: {env}")
        # Note: No cleanup needed for Temporal environment unlike K8s namespaces


def generate_test_workflow_id(prefix: str = "test-workflow") -> str:
    """
    Generate a unique test workflow ID.
    
    Args:
        prefix: Prefix for the workflow ID
        
    Returns:
        Unique workflow ID suitable for testing
    """
    timestamp = int(time.time())
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}-{timestamp}-{unique_id}"


def generate_test_query(workflow_type: Optional[str] = None,
                       execution_status: Optional[str] = None,
                       start_time_after: Optional[str] = None) -> str:
    """
    Generate a test workflow query string.
    
    Args:
        workflow_type: Workflow type to filter by
        execution_status: Execution status to filter by
        start_time_after: Start time filter (ISO format)
        
    Returns:
        Valid Temporal workflow query string
    """
    conditions = []
    
    if workflow_type:
        conditions.append(f"WorkflowType = '{workflow_type}'")
    
    if execution_status:
        conditions.append(f"ExecutionStatus = '{execution_status}'")
    
    if start_time_after:
        conditions.append(f"StartTime > '{start_time_after}'")
    
    return " AND ".join(conditions)


def generate_test_structured_query(workflow_types: Optional[List[str]] = None,
                                  statuses: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generate a test structured query for the query builder.
    
    Args:
        workflow_types: List of workflow types
        statuses: List of execution statuses
        
    Returns:
        Structured query dictionary
    """
    query = {
        "field_filters": [],
        "logical_operator": "AND"
    }
    
    if workflow_types:
        if len(workflow_types) == 1:
            query["field_filters"].append({
                "field": "WorkflowType",
                "operator": "=",
                "value": workflow_types[0]
            })
        else:
            query["in_filters"] = [{
                "field": "WorkflowType",
                "values": workflow_types
            }]
    
    if statuses:
        if len(statuses) == 1:
            query["field_filters"].append({
                "field": "ExecutionStatus", 
                "operator": "=",
                "value": statuses[0]
            })
        else:
            if "in_filters" not in query:
                query["in_filters"] = []
            query["in_filters"].append({
                "field": "ExecutionStatus",
                "values": statuses
            })
    
    return query


def validate_mcp_response(response: Dict[str, Any], 
                         expected_schema: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that an MCP response meets expected format.
    
    Args:
        response: The MCP response to validate
        expected_schema: Optional schema to validate against
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Basic MCP response validation
        if not isinstance(response, dict):
            return False, "Response is not a dictionary"
        
        # Check for required MCP fields
        if "jsonrpc" not in response:
            return False, "Missing 'jsonrpc' field"
        
        if response["jsonrpc"] != "2.0":
            return False, f"Invalid jsonrpc version: {response['jsonrpc']}"
        
        # Check for either result or error
        has_result = "result" in response
        has_error = "error" in response
        
        if not has_result and not has_error:
            return False, "Response must have either 'result' or 'error' field"
        
        if has_result and has_error:
            return False, "Response cannot have both 'result' and 'error' fields"
        
        # If there's an error, validate error structure
        if has_error:
            error = response["error"]
            if not isinstance(error, dict):
                return False, "Error field must be a dictionary"
            
            if "code" not in error or "message" not in error:
                return False, "Error must have 'code' and 'message' fields"
        
        # Additional schema validation if provided
        if expected_schema and has_result:
            result = response["result"]
            for key, expected_type in expected_schema.items():
                if key not in result:
                    return False, f"Missing expected field '{key}' in result"
                
                if not isinstance(result[key], expected_type):
                    return False, f"Field '{key}' has wrong type: expected {expected_type.__name__}, got {type(result[key]).__name__}"
        
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_temporal_workflow_response(response: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a Temporal workflow command response.
    
    Args:
        response: The response from a temporal workflow command
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # First validate as MCP response
        is_valid, error = validate_mcp_response(response)
        if not is_valid:
            return False, error
        
        # If there's an error in the response, that's still valid
        if "error" in response:
            return True, None
        
        result = response.get("result", {})
        
        # Check for typical temporal response structure
        if "success" in result:
            if not isinstance(result["success"], bool):
                return False, "Success field must be boolean"
        
        # If successful, should have data or be a simple operation
        if result.get("success") is True:
            if "data" not in result and "message" not in result:
                return False, "Successful response should have 'data' or 'message'"
        
        return True, None
        
    except Exception as e:
        return False, f"Temporal response validation error: {str(e)}"


def wait_for_condition(condition_func: Callable[[], bool], 
                      timeout: int = 30,
                      poll_interval: float = 1.0,
                      description: str = "condition") -> bool:
    """
    Wait for a condition to become true.
    
    Args:
        condition_func: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        poll_interval: Time between checks in seconds
        description: Description of the condition for logging
        
    Returns:
        True if condition was met, False if timeout
    """
    if MOCK_MODE:
        logger.info(f"[MOCK] Condition '{description}' met immediately")
        return True
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if condition_func():
                logger.info(f"Condition '{description}' met after {time.time() - start_time:.1f}s")
                return True
        except Exception as e:
            logger.warning(f"Error checking condition '{description}': {e}")
        
        time.sleep(poll_interval)
    
    logger.error(f"Timeout waiting for condition '{description}' after {timeout}s")
    return False


def assert_tool_exists(tools_list: List[Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
    """
    Assert that a specific tool exists in the tools list.
    
    Args:
        tools_list: List of tools from MCP server
        tool_name: Name of the tool to find
        
    Returns:
        The tool definition
        
    Raises:
        AssertionError: If tool is not found
    """
    for tool in tools_list:
        if tool.get("name") == tool_name:
            return tool
    
    available_tools = [tool.get("name") for tool in tools_list]
    raise AssertionError(f"Tool '{tool_name}' not found. Available tools: {available_tools}")


def generate_test_time_range() -> Tuple[str, str]:
    """
    Generate a test time range (last 24 hours).
    
    Returns:
        Tuple of (start_time, end_time) in ISO format
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    return (
        start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    )


def create_test_environment_config() -> Dict[str, Any]:
    """
    Create test environment configuration.
    
    Returns:
        Configuration dictionary for tests
    """
    return {
        "temporal_env": os.environ.get("TEMPORAL_TEST_ENV", "staging"),
        "timeout": int(os.environ.get("TEMPORAL_TEST_TIMEOUT", "30")),
        "mock_mode": MOCK_MODE,
        "retry_attempts": int(os.environ.get("TEMPORAL_TEST_RETRIES", "3")),
        "log_level": os.environ.get("TEMPORAL_TEST_LOG_LEVEL", "INFO")
    }


# Mock data generators for testing
def generate_mock_workflow_list() -> Dict[str, Any]:
    """Generate mock workflow list response."""
    return {
        "success": True,
        "data": {
            "workflows": [
                {
                    "execution": {
                        "workflow_id": f"test-workflow-{i}",
                        "run_id": f"run-{uuid.uuid4().hex[:8]}",
                        "workflow_type": {"name": f"TestWorkflowType{i % 3}"}
                    },
                    "status": {"name": "Running" if i % 2 == 0 else "Completed"},
                    "start_time": datetime.utcnow().isoformat() + "Z"
                }
                for i in range(5)
            ]
        }
    }


def generate_mock_workflow_description() -> Dict[str, Any]:
    """Generate mock workflow description response."""
    return {
        "success": True,
        "data": {
            "workflow_execution_info": {
                "execution": {
                    "workflow_id": "test-workflow-1",
                    "run_id": f"run-{uuid.uuid4().hex[:8]}"
                },
                "type": {"name": "TestWorkflowType"},
                "status": "Running",
                "start_time": datetime.utcnow().isoformat() + "Z"
            }
        }
    }


if __name__ == "__main__":
    # Test the utilities
    print("Testing temporal-cli-mcp test utilities...")
    
    # Test environment setup
    config = create_test_environment_config()
    print(f"✓ Test configuration: {config}")
    
    # Test data generation
    workflow_id = generate_test_workflow_id()
    print(f"✓ Generated workflow ID: {workflow_id}")
    
    query = generate_test_query("TestWorkflow", "Running")
    print(f"✓ Generated query: {query}")
    
    structured_query = generate_test_structured_query(["Type1", "Type2"], ["Running"])
    print(f"✓ Generated structured query: {structured_query}")
    
    # Test validation
    mock_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"success": True, "data": {}}
    }
    is_valid, error = validate_mcp_response(mock_response)
    print(f"✓ MCP response validation: {is_valid} (error: {error})")
    
    print("✓ Test utilities validation completed")