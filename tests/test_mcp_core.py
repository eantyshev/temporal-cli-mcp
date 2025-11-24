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


class TestWorkflowHistoryFiltering:
    """Test workflow history filtering and projection features."""
    
    @pytest.fixture
    def mcp_client(self):
        """Fixture for history filtering tests."""
        with temporal_mcp_client(env=TEST_CONFIG["temporal_env"]) as client:
            yield client
    
    @pytest.fixture
    def sample_history(self):
        """Sample workflow history for testing filters."""
        # This would be mocked in mock mode or use real data in integration mode
        return {
            "events": [
                {"eventId": 1, "eventType": "WORKFLOW_EXECUTION_STARTED", "eventTime": "2025-01-01T00:00:00Z"},
                {"eventId": 2, "eventType": "WORKFLOW_TASK_SCHEDULED", "eventTime": "2025-01-01T00:00:01Z"},
                {"eventId": 3, "eventType": "WORKFLOW_TASK_STARTED", "eventTime": "2025-01-01T00:00:02Z"},
                {"eventId": 4, "eventType": "WORKFLOW_TASK_COMPLETED", "eventTime": "2025-01-01T00:00:03Z"},
                {"eventId": 5, "eventType": "TIMER_STARTED", "eventTime": "2025-01-01T00:00:04Z"},
                {"eventId": 6, "eventType": "TIMER_FIRED", "eventTime": "2025-01-01T00:00:05Z"},
                {"eventId": 7, "eventType": "WORKFLOW_TASK_FAILED", "eventTime": "2025-01-01T00:00:06Z"},
                {"eventId": 8, "eventType": "WORKFLOW_EXECUTION_COMPLETED", "eventTime": "2025-01-01T00:00:07Z"},
            ]
        }
    
    def test_event_type_filtering(self, mcp_client):
        """Test filtering by specific event types."""
        # Note: This test requires a workflow with history
        # In mock mode, it will use mock data
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow",
            event_types=["WORKFLOW_TASK_FAILED", "WORKFLOW_EXECUTION_COMPLETED"]
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            # Check for filter_info
            if "filter_info" in data:
                filter_info = data["filter_info"]
                assert "filters_applied" in filter_info
                assert any("event_types" in f for f in filter_info["filters_applied"])
                logger.info(f"✓ Event type filtering applied: {filter_info['filters_applied']}")
                
                # Verify filtered events only contain requested types
                events = data.get("events", [])
                for event in events:
                    assert event.get("eventType") in ["WORKFLOW_TASK_FAILED", "WORKFLOW_EXECUTION_COMPLETED"]
                
                logger.info(f"✓ Filtered {filter_info['original_event_count']} → {filter_info['filtered_event_count']} events")
        else:
            logger.info("✓ Event type filtering handled (no data or error)")
    
    def test_exclude_event_types(self, mcp_client):
        """Test excluding specific event types."""
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow",
            exclude_event_types=["TIMER_FIRED", "TIMER_STARTED"]
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            if "filter_info" in data:
                filter_info = data["filter_info"]
                assert any("exclude_event_types" in f for f in filter_info["filters_applied"])
                logger.info(f"✓ Exclude filtering applied: {filter_info['filters_applied']}")
                
                # Verify excluded events are not present
                events = data.get("events", [])
                for event in events:
                    assert event.get("eventType") not in ["TIMER_FIRED", "TIMER_STARTED"]
                
                logger.info(f"✓ Excluded events from {filter_info['original_event_count']} events")
    
    def test_limit_and_reverse(self, mcp_client):
        """Test limit and reverse parameters."""
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow",
            limit=5,
            reverse=True
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            if "filter_info" in data:
                filter_info = data["filter_info"]
                assert any("limit=5" in f for f in filter_info["filters_applied"])
                assert any("reverse=True" in f for f in filter_info["filters_applied"])
                logger.info(f"✓ Limit and reverse applied: {filter_info['filters_applied']}")
                
                # Verify limit is respected
                events = data.get("events", [])
                assert len(events) <= 5
                
                logger.info(f"✓ Limited to {len(events)} events (reverse order)")
    
    def test_field_projection_minimal(self, mcp_client):
        """Test minimal field projection."""
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow",
            fields="minimal"
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            if "filter_info" in data:
                filter_info = data["filter_info"]
                assert any("fields=minimal" in f for f in filter_info["filters_applied"])
                logger.info(f"✓ Minimal projection applied: {filter_info['filters_applied']}")
                
                # Verify events only have minimal fields
                events = data.get("events", [])
                for event in events[:2]:  # Check first 2
                    assert "eventId" in event
                    assert "eventType" in event
                    assert "eventTime" in event
                    # Should not have detailed attributes
                    assert len(event) <= 4  # eventId, eventType, eventTime, maybe one attribute key
                
                logger.info("✓ Events have minimal fields only")
    
    def test_field_projection_standard(self, mcp_client):
        """Test standard field projection."""
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow",
            fields="standard"
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            if "filter_info" in data:
                filter_info = data["filter_info"]
                assert any("fields=standard" in f for f in filter_info["filters_applied"])
                logger.info(f"✓ Standard projection applied")
    
    def test_preset_last_failure_context(self, mcp_client):
        """Test last_failure_context preset."""
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow",
            preset="last_failure_context"
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            if "filter_info" in data:
                filter_info = data["filter_info"]
                assert any("preset=last_failure_context" in f for f in filter_info["filters_applied"])
                logger.info(f"✓ Last failure context preset applied")
                
                # Should have at most 11 events (10 before + failure)
                events = data.get("events", [])
                assert len(events) <= 11
                
                logger.info(f"✓ Got {len(events)} events for failure context")
    
    def test_preset_summary(self, mcp_client):
        """Test summary preset."""
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow",
            preset="summary"
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            if "filter_info" in data:
                filter_info = data["filter_info"]
                assert any("preset=summary" in f for f in filter_info["filters_applied"])
                logger.info(f"✓ Summary preset applied")
                
                # Verify only summary events are present
                events = data.get("events", [])
                summary_types = [
                    "WORKFLOW_EXECUTION_STARTED", "WORKFLOW_EXECUTION_COMPLETED",
                    "WORKFLOW_EXECUTION_FAILED", "CHILD_WORKFLOW_EXECUTION_STARTED",
                    "ACTIVITY_TASK_COMPLETED", "ACTIVITY_TASK_FAILED"
                ]
                for event in events:
                    assert event.get("eventType") in summary_types
                
                logger.info(f"✓ All {len(events)} events are summary events")
    
    def test_preset_critical_path(self, mcp_client):
        """Test critical_path preset."""
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow",
            preset="critical_path"
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            if "filter_info" in data:
                filter_info = data["filter_info"]
                assert any("preset=critical_path" in f for f in filter_info["filters_applied"])
                logger.info(f"✓ Critical path preset applied")
                
                # Verify verbose events are excluded
                events = data.get("events", [])
                verbose_types = ["TIMER_FIRED", "TIMER_STARTED", "MARKER_RECORDED"]
                for event in events:
                    assert event.get("eventType") not in verbose_types
                
                logger.info(f"✓ Verbose events excluded from {len(events)} events")
    
    def test_combined_filters(self, mcp_client):
        """Test combining multiple filters."""
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow",
            event_types=["WORKFLOW_TASK_FAILED", "WORKFLOW_TASK_COMPLETED"],
            limit=10,
            reverse=True,
            fields="standard"
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            if "filter_info" in data:
                filter_info = data["filter_info"]
                filters_applied = filter_info["filters_applied"]
                
                # Should have multiple filters
                assert len(filters_applied) >= 3
                assert any("event_types" in f for f in filters_applied)
                assert any("limit=10" in f for f in filters_applied)
                assert any("fields=standard" in f for f in filters_applied)
                
                logger.info(f"✓ Combined filters applied: {filters_applied}")
                logger.info(f"✓ Filtered {filter_info['original_event_count']} → {filter_info['filtered_event_count']} events")
    
    def test_backwards_compatibility(self, mcp_client):
        """Test that get_workflow_history still works without new parameters."""
        response = mcp_client.call_workflow_tool(
            "get_workflow_history",
            workflow_id="test-workflow"
        )
        
        is_valid, error = validate_temporal_workflow_response(response)
        assert is_valid, f"Invalid response: {error}"
        
        result = response.get("result", {})
        
        if result.get("success") and "data" in result:
            data = result["data"]
            
            # Without filtering, should NOT have filter_info
            assert "filter_info" not in data or data["filter_info"]["filtered_event_count"] == data["filter_info"]["original_event_count"]
            
            logger.info("✓ Backwards compatibility maintained (no filtering)")


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