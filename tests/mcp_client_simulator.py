#!/usr/bin/env python3
"""
MCP Client Simulator for testing the temporal-cli-mcp.

This module provides a client that can communicate with the MCP server
through stdio transport, simulating an MCP client for testing purposes.
Adapted from kubectl-mcp-server design patterns.
"""

import os
import json
import uuid
import time
import logging
import subprocess
import select
import io
from typing import Dict, List, Any, Optional, Union, Tuple
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Check if we're running in mock mode
MOCK_MODE = os.environ.get("TEMPORAL_MCP_TEST_MOCK_MODE", "0") == "1"


class TemporalMCPClientSimulator:
    """
    Simulates an MCP client for testing temporal-cli-mcp.
    Supports stdio transport with the Temporal MCP server.
    """
    
    def __init__(self, 
                 stdio_cmd: Optional[List[str]] = None,
                 env: str = "staging",
                 timeout: int = 30):
        """
        Initialize the MCP client simulator.
        
        Args:
            stdio_cmd: Command to start the MCP server for stdio transport
            env: Temporal environment to use (staging, prod, etc.)
            timeout: Request timeout in seconds
        """
        self.env = env
        self.timeout = timeout
        self.server_process = None
        self._request_id = 1
        
        # Default command if none provided
        if stdio_cmd is None:
            stdio_cmd = ["python", "-m", "temporal_cli_mcp", "--env", env]
        self.stdio_cmd = stdio_cmd
        
        if not MOCK_MODE:
            self._start_server_process()
    
    def _start_server_process(self):
        """Start the server process for stdio transport."""
        import copy
        import sys
        
        # Use sys.executable for consistency
        if self.stdio_cmd and self.stdio_cmd[0] == "python":
            self.stdio_cmd = [sys.executable, "-I"] + self.stdio_cmd[1:]
        
        # Setup environment
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        logger.info(f"Project root: {project_root}")
        logger.info(f"Starting Temporal MCP server: {' '.join(self.stdio_cmd)}")
        
        env = copy.deepcopy(os.environ)
        env["PYTHONPATH"] = project_root
        env["PYTHONNOUSERSITE"] = "1"
        # Ensure test mode doesn't conflict with production
        env["TEMPORAL_MCP_TEST_MODE"] = "1"
        
        self.server_process = subprocess.Popen(
            self.stdio_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env
        )
        
        # Wait for server to initialize
        time.sleep(2)
        
        if self.server_process.poll() is not None:
            stdout = self.server_process.stdout.read() if self.server_process.stdout else ""
            stderr = self.server_process.stderr.read() if self.server_process.stderr else ""
            raise RuntimeError(
                f"Server process failed to start. "
                f"Command: {' '.join(self.stdio_cmd)}\n"
                f"Stdout: {stdout}\n"
                f"Stderr: {stderr}"
            )
        
        logger.info("Temporal MCP server started successfully")
    
    def _write_message(self, payload: Dict[str, Any]) -> None:
        """Write a message to the MCP server."""
        if MOCK_MODE:
            logger.info(f"[MOCK] Would send message: {payload}")
            return
        
        if not self.server_process or not self.server_process.stdin:
            raise RuntimeError("Server process is not available")
        
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        
        self.server_process.stdin.write(header.decode("ascii"))
        self.server_process.stdin.write(body.decode("utf-8"))
        self.server_process.stdin.flush()
    
    def _read_message(self) -> Dict[str, Any]:
        """Read a message from the MCP server."""
        if MOCK_MODE:
            # Return mock response
            return {
                "jsonrpc": "2.0",
                "id": self._request_id - 1,
                "result": {"mock": True, "message": "Mock response"}
            }
        
        if not self.server_process or not self.server_process.stdout:
            raise RuntimeError("Server process is not available")
        
        reader = self.server_process.stdout
        content_length = None
        timeout = self.timeout
        saw_content_length = False
        end_of_headers = False
        
        while not end_of_headers:
            rlist, _, _ = select.select([reader], [], [], timeout)
            if not rlist:
                # Dump stderr for debugging
                if self.server_process.stderr:
                    try:
                        err = self.server_process.stderr.read()
                        if err:
                            logger.error(f"[server stderr] {err}")
                    except Exception:
                        pass
                raise TimeoutError("Timed out waiting for server response header")
            
            line = reader.readline()
            if line in ("\r\n", "\n", ""):
                if saw_content_length:
                    end_of_headers = True
                    break
                else:
                    continue
            
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                    saw_content_length = True
                except Exception as e:
                    logger.error(f"Failed to parse Content-Length: {e}")
        
        if content_length is None:
            raise RuntimeError("No Content-Length header in response")
        
        body = reader.read(content_length)
        return json.loads(body)
    
    def _next_request_id(self) -> int:
        """Get the next request ID."""
        request_id = self._request_id
        self._request_id += 1
        return request_id
    
    def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP session."""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "temporal-mcp-test", "version": "1.0"},
            },
        }
        
        self._write_message(request)
        response = self._read_message()
        
        # Send initialized notification
        self._write_message({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        })
        
        return response
    
    def list_tools(self) -> Dict[str, Any]:
        """List available tools from the MCP server."""
        if MOCK_MODE:
            return {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "result": {
                    "tools": [
                        {"name": "list_workflows", "description": "List workflows"},
                        {"name": "count_workflows", "description": "Count workflows"},
                        {"name": "describe_workflow", "description": "Describe workflow"},
                        {"name": "get_workflow_history", "description": "Get workflow history"},
                        {"name": "build_workflow_query", "description": "Build workflow query"},
                        {"name": "validate_workflow_query", "description": "Validate workflow query"}
                    ]
                }
            }
        
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/list",
            "params": {},
        }
        
        self._write_message(request)
        return self._read_message()
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool on the MCP server."""
        if arguments is None:
            arguments = {}
        
        if MOCK_MODE:
            return {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "result": get_mock_response(tool_name)
            }
        
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
        }
        
        self._write_message(request)
        return self._read_message()
    
    def call_workflow_tool(self, 
                          tool_name: str, 
                          **kwargs) -> Dict[str, Any]:
        """
        Convenience method to call workflow-related tools.
        
        Args:
            tool_name: Name of the workflow tool to call
            **kwargs: Arguments to pass to the tool
        """
        return self.call_tool(tool_name, kwargs)
    
    def close(self):
        """Close the MCP client and cleanup resources."""
        if not MOCK_MODE and self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Server process did not terminate gracefully, killing...")
                self.server_process.kill()
            except Exception as e:
                logger.error(f"Error closing server process: {e}")
            finally:
                self.server_process = None
    
    def __enter__(self):
        """Context manager entry."""
        if not MOCK_MODE:
            self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


@contextmanager
def temporal_mcp_client(env: str = "staging", 
                       timeout: int = 30) -> TemporalMCPClientSimulator:
    """
    Context manager for creating and managing a Temporal MCP client.
    
    Args:
        env: Temporal environment to use
        timeout: Request timeout in seconds
    
    Yields:
        TemporalMCPClientSimulator instance
    """
    client = TemporalMCPClientSimulator(env=env, timeout=timeout)
    try:
        yield client
    finally:
        client.close()


# Mock responses for testing without actual Temporal CLI
MOCK_RESPONSES = {
    "list_workflows": {
        "success": True,
        "data": {
            "workflows": [
                {
                    "execution": {
                        "workflow_id": "test-workflow-1",
                        "run_id": "abc123",
                        "workflow_type": {"name": "TestWorkflow"}
                    },
                    "status": {"name": "Running"}
                }
            ]
        }
    },
    "describe_workflow": {
        "success": True,
        "data": {
            "workflow_execution_info": {
                "execution": {
                    "workflow_id": "test-workflow-1",
                    "run_id": "abc123"
                },
                "type": {"name": "TestWorkflow"},
                "status": "Running"
            }
        }
    },
    "count_workflows": {
        "success": True,
        "data": {"count": 5}
    }
}


def get_mock_response(tool_name: str) -> Dict[str, Any]:
    """Get a mock response for a given tool name."""
    return MOCK_RESPONSES.get(tool_name, {
        "success": True,
        "data": {"mock": True, "tool": tool_name}
    })


if __name__ == "__main__":
    # Simple test of the client simulator
    print("Testing Temporal MCP Client Simulator...")
    
    with temporal_mcp_client() as client:
        # Test initialization
        print("✓ Client initialized")
        
        # Test listing tools
        tools_response = client.list_tools()
        print(f"✓ Tools listed: {len(tools_response.get('result', {}).get('tools', []))} tools")
        
        # Test calling a tool
        if not MOCK_MODE:
            try:
                response = client.call_workflow_tool("count_workflows")
                print(f"✓ Tool called successfully: {response}")
            except Exception as e:
                print(f"⚠ Tool call failed (expected in test): {e}")
        
        print("✓ Client simulator test completed")