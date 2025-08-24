#!/usr/bin/env python3
"""
Core MCP tests for temporal-cli-mcp.
Tests basic functionality like MCP protocol compliance,
tool availability, and basic workflow operations.
"""

import os
import json
import pytest
import logging
from typing import Dict, Any

from .mcp_client_simulator import TemporalMCPClientSimulator, temporal_mcp_client
from .test_utils import (
    temporal_test_context, validate_mcp_response, validate_temporal_workflow_response,
    assert_tool_exists, generate_test_query, create_test_environment_config
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = create_test_environment_config()


class TestTemporalMCPCore:
    """
    Test Temporal CLI MCP core functionality through MCP protocol.
    Tests basic operations like MCP initialization, tool discovery,
    and fundamental workflow operations.
    """
    
    @pytest.fixture(scope="class")
    def mcp_client(self):
        """Fixture to create and manage MCP client."""
        with temporal_mcp_client(
            env=TEST_CONFIG["temporal_env"], 
            timeout=TEST_CONFIG["timeout"]
        ) as client:
            yield client
    
    @pytest.fixture
    def test_environment(self):
        """Setup test environment for each test."""
        with temporal_test_context(env=TEST_CONFIG["temporal_env"]) as env:
            yield env
    
    def test_mcp_initialization(self, mcp_client):
        """Test MCP protocol initialization."""
        # The client fixture handles initialization, so we just verify it worked
        assert mcp_client is not None
        logger.info("✓ MCP client initialized successfully")
    
    def test_list_tools(self, mcp_client):
        """Test listing available tools."""
        response = mcp_client.list_tools()
        
        # Validate MCP response format
        is_valid, error = validate_mcp_response(response)
        assert is_valid, f"Invalid MCP response: {error}"
        
        # Check response structure
        assert "result" in response, "Response should contain 'result' field"
        assert "tools" in response["result"], "Result should contain 'tools' field"
        
        tools = response["result"]["tools"]
        assert isinstance(tools, list), "Tools should be a list"
        assert len(tools) > 0, "Tools list should not be empty"
        
        # Check each tool has required fields
        for tool in tools:
            assert "name" in tool, "Tool should have a name"
            assert "description" in tool, "Tool should have a description"
        
        logger.info(f"✓ Found {len(tools)} tools")
        
        # Verify expected workflow tools exist
        expected_tools = [
            "list_workflows",
            "describe_workflow", 
            "get_workflow_history",
            "count_workflows",
            "build_workflow_query",
            "validate_workflow_query"
        ]
        
        for tool_name in expected_tools:
            tool = assert_tool_exists(tools, tool_name)
            logger.info(f"✓ Tool '{tool_name}' found: {tool['description'][:60]}...")
    
    def test_count_workflows(self, mcp_client, test_environment):
        """Test workflow counting functionality."""
        response = mcp_client.call_workflow_tool("count_workflows")
        
        # Validate response format
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid workflow response: {error}"
        
        # Check response structure
        result = response.get("result", {})
        
        if result.get("success"):
            assert "data" in result, "Successful response should have data"
            data = result["data"]
            assert "count" in data, "Count response should have count field"
            assert isinstance(data["count"], int), "Count should be an integer"
            logger.info(f"✓ Workflow count: {data['count']}")
        else:
            # In case of error, check error structure
            assert "error" in result, "Failed response should have error"
            logger.info(f"✓ Count operation failed as expected: {result.get('error')}")
    
    def test_list_workflows_basic(self, mcp_client, test_environment):
        """Test basic workflow listing."""
        response = mcp_client.call_workflow_tool("list_workflows", limit=5)
        
        # Validate response format
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid workflow response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success"):
            assert "data" in result, "Successful response should have data"
            data = result["data"]
            
            # Check for workflows field (might be empty)
            if "workflows" in data:
                workflows = data["workflows"]
                assert isinstance(workflows, list), "Workflows should be a list"
                logger.info(f"✓ Listed {len(workflows)} workflows")
                
                # If there are workflows, validate structure
                for workflow in workflows[:2]:  # Check first 2
                    assert "execution" in workflow, "Workflow should have execution info"
                    execution = workflow["execution"]
                    assert "workflow_id" in execution, "Execution should have workflow_id"
                    logger.info(f"  - {execution['workflow_id']}")
            else:
                logger.info("✓ No workflows found (empty result)")
        else:
            logger.info(f"✓ List operation handled error: {result.get('error')}")
    
    def test_list_workflows_with_query(self, mcp_client, test_environment):
        """Test workflow listing with query filter."""
        # Generate a test query
        test_query = generate_test_query("TestWorkflow", "Running")
        
        response = mcp_client.call_workflow_tool(
            "list_workflows", 
            query=test_query,
            limit=3
        )
        
        # Validate response format
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid workflow response: {error}"
        
        result = response.get("result", {})
        logger.info(f"✓ Query-filtered list completed: success={result.get('success')}")
    
    def test_query_builder_tools(self, mcp_client, test_environment):
        """Test query builder and validation tools."""
        # Test query validation
        test_query = "WorkflowType = 'TestWorkflow'"
        
        response = mcp_client.call_workflow_tool(
            "validate_workflow_query",
            query=test_query
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid query validation response: {error}"
        
        logger.info("✓ Query validation tool working")
        
        # Test query building
        structured_query = {
            "field_filters": [
                {"field": "WorkflowType", "operator": "=", "value": "TestWorkflow"}
            ]
        }
        
        response = mcp_client.call_workflow_tool(
            "build_workflow_query",
            structured_query=structured_query
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid query building response: {error}"
        
        logger.info("✓ Query building tool working")
    
    def test_error_handling(self, mcp_client, test_environment):
        """Test error handling with invalid parameters."""
        # Test with invalid workflow ID
        response = mcp_client.call_workflow_tool(
            "describe_workflow",
            workflow_id="invalid-workflow-id-that-should-not-exist"
        )
        
        # Should get a valid MCP response even if the operation fails
        is_valid, error = validate_mcp_response(response)
        assert is_valid, f"Invalid MCP response for error case: {error}"
        
        logger.info("✓ Error handling works correctly")
    
    @pytest.mark.skipif(
        TEST_CONFIG["mock_mode"], 
        reason="Skipping integration test in mock mode"
    )
    def test_temporal_cli_integration(self, mcp_client, test_environment):
        """Test integration with actual Temporal CLI (skipped in mock mode)."""
        # This test only runs when we have real Temporal CLI access
        response = mcp_client.call_workflow_tool("count_workflows")
        
        result = response.get("result", {})
        
        # In real mode, we expect either success or a meaningful error
        assert "success" in result, "Response should indicate success status"
        
        if result["success"]:
            assert "data" in result, "Successful response should have data"
            logger.info("✓ Real Temporal CLI integration working")
        else:
            # Even failures should be structured properly
            assert "error" in result, "Failed response should have error details"
            logger.info(f"✓ Temporal CLI error handled: {result['error']}")


class TestTemporalMCPEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.fixture
    def mcp_client(self):
        """Fixture for edge case testing."""
        with temporal_mcp_client(env=TEST_CONFIG["temporal_env"]) as client:
            yield client
    
    def test_empty_parameters(self, mcp_client):
        """Test tools with empty or minimal parameters."""
        # Test count with no parameters
        response = mcp_client.call_workflow_tool("count_workflows")
        is_valid, _ = validate_mcp_response(response)
        assert is_valid, "Empty parameter count should return valid response"
        
        # Test list with just limit
        response = mcp_client.call_workflow_tool("list_workflows", limit=1)
        is_valid, _ = validate_mcp_response(response)
        assert is_valid, "Minimal parameter list should return valid response"
        
        logger.info("✓ Empty parameter handling works")
    
    def test_invalid_tool_name(self, mcp_client):
        """Test calling non-existent tools."""
        response = mcp_client.call_tool("non_existent_tool", {})
        
        # In mock mode, we get a success response with mock data
        # In real mode, we should get an error response
        if TEST_CONFIG["mock_mode"]:
            # Mock mode returns success with mock data
            is_valid, _ = validate_mcp_response(response)
            assert is_valid, "Mock response should be valid MCP response"
            result = response.get("result", {})
            assert result.get("data", {}).get("mock") is True, "Should indicate mock response"
            logger.info("✓ Invalid tool name handling works (mock mode)")
        else:
            # Real mode should return error
            assert "error" in response, "Non-existent tool should return error"
            error = response["error"]
            assert "code" in error and "message" in error, "Error should have code and message"
            logger.info("✓ Invalid tool name handling works (real mode)")
    
    def test_malformed_parameters(self, mcp_client):
        """Test with malformed parameter values."""
        # Test with invalid limit type
        response = mcp_client.call_workflow_tool("list_workflows", limit="not-a-number")
        
        # Should handle gracefully (either convert or error appropriately)
        is_valid, _ = validate_mcp_response(response)
        assert is_valid, "Malformed parameters should be handled gracefully"
        
        logger.info("✓ Malformed parameter handling works")


if __name__ == "__main__":
    # Simple test run
    print("Running basic MCP core tests...")
    
    config = create_test_environment_config()
    print(f"Test configuration: {config}")
    
    try:
        with temporal_mcp_client(env=config["temporal_env"]) as client:
            print("✓ MCP client created successfully")
            
            # Test tool listing
            response = client.list_tools()
            tools = response.get("result", {}).get("tools", [])
            print(f"✓ Found {len(tools)} tools")
            
            # Test basic workflow operation
            response = client.call_workflow_tool("count_workflows")
            print(f"✓ Count workflows response: {response.get('result', {}).get('success')}")
            
        print("✓ Basic test completed successfully")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()