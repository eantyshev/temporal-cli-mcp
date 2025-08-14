import base64
import json
from typing import Any, Dict, Optional

from ..core import mcp

# Maximum length for decoded strings to prevent memory issues
MAX_DECODED_STRING_LENGTH = 4000


def _truncate_string_if_needed(text: str) -> str:
    """Truncate string if it exceeds the maximum length limit."""
    if len(text) <= MAX_DECODED_STRING_LENGTH:
        return text
    
    truncated = text[:MAX_DECODED_STRING_LENGTH]
    return f"{truncated}... [truncated: showing first {MAX_DECODED_STRING_LENGTH} of {len(text)} characters]"


@mcp.tool()
async def get_workflow_history(
    workflow_id: str,
    run_id: Optional[str] = None,
    decode_payloads: bool = True,
) -> Dict[str, Any]:
    """Get workflow execution history with automatic base64 payload decoding.
    
    This tool retrieves the complete event history for a workflow execution,
    including automatic decoding of base64-encoded payloads for easier analysis.
    Use this for workflow inspection, debugging, and analysis.
    
    Args:
        workflow_id: The workflow ID to retrieve history for
        run_id: Optional specific run ID to target
        decode_payloads: Whether to automatically decode base64 payloads (default: True)
    """
    import json
    import base64
    from ..models import WorkflowHistoryRequest
    from ..base import AsyncCommandExecutor
    from ..command_builder import TemporalCommandBuilder
    from ..config import config
    from ..exceptions import ValidationError
    
    def _sanitize_for_fastmcp(obj):
        """Remove bytes objects that cause FastMCP to fail during iteration."""
        if isinstance(obj, dict):
            return {k: _sanitize_for_fastmcp(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_sanitize_for_fastmcp(v) for v in obj]
        elif isinstance(obj, (bytes, bytearray)):
            return base64.b64encode(obj).decode('utf-8')
        else:
            return obj
    
    try:
        # Validate input
        request = WorkflowHistoryRequest(
            workflow_id=workflow_id,
            run_id=run_id,
            decode_payloads=decode_payloads
        )
        
        # Create executor and builder
        executor = AsyncCommandExecutor()
        builder = TemporalCommandBuilder(env=config.env)
        
        # Build and execute command
        workflow_args = builder.build_workflow_history(request.workflow_id, request.run_id)
        cmd = builder.build_full_command(workflow_args)
        result = await executor.execute(cmd)
        
        if not result["success"]:
            raise Exception(f"Failed to get workflow history: {result['stderr']}")
        
        # Return result without modification if decoding is not requested
        if not request.decode_payloads:
            return result
        
        # Decode payloads if requested
        if "data" in result and "events" in result["data"]:
            # Create a new result structure
            new_result = {
                "success": result["success"],
                "returncode": result["returncode"], 
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "cmd": result["cmd"],
                "data": {
                    "events": _decode_event_payloads(result["data"]["events"])
                }
            }
            # Copy any other keys from the original data
            for key, value in result["data"].items():
                if key != "events":
                    new_result["data"][key] = value
            # Copy any other keys from the original result  
            for key, value in result.items():
                if key not in new_result:
                    new_result[key] = value
            
            # WORKAROUND: Sanitize the result to avoid FastMCP's dictionary iteration bug
            return _sanitize_for_fastmcp(new_result)
        
        return result
        
    except Exception as e:
        if "ValidationError" in str(type(e)):
            raise ValidationError(f"Invalid input: {e}")
        raise


def _decode_event_payloads(events: list) -> list:
    """Decode base64 payloads in workflow events."""
    if not isinstance(events, list):
        return events
    
    decoded_events = []
    for event in events:
        if isinstance(event, dict):
            decoded_event = _decode_single_event_payloads(event)
            decoded_events.append(decoded_event)
        else:
            decoded_events.append(event)
    
    return decoded_events


def _decode_single_event_payloads(event: dict) -> dict:
    """Decode base64 payloads in a single workflow event."""
    import copy
    # Create a deep copy to avoid modifying the original and any shared nested structures
    decoded_event = copy.deepcopy(event)
    
    # Common payload locations in workflow events
    payload_paths = [
        # Workflow execution started
        ["workflowExecutionStartedEventAttributes", "input", "payloads"],
        ["workflowExecutionStartedEventAttributes", "memo", "fields"],
        # Child workflow execution
        ["startChildWorkflowExecutionInitiatedEventAttributes", "input", "payloads"],
        ["childWorkflowExecutionCompletedEventAttributes", "result", "payloads"],
        # Activity task
        ["activityTaskScheduledEventAttributes", "input", "payloads"],
        ["activityTaskCompletedEventAttributes", "result", "payloads"],
        # Signal workflow
        ["signalExternalWorkflowExecutionInitiatedEventAttributes", "input", "payloads"],
        # Query workflow  
        ["workflowExecutionSignaledEventAttributes", "input", "payloads"],
        # Workflow execution completed
        ["workflowExecutionCompletedEventAttributes", "result", "payloads"],
        # Workflow execution failed
        ["workflowExecutionFailedEventAttributes", "failure", "cause", "encodedAttributes"],
    ]
    
    # Process each potential payload location
    for path in payload_paths:
        _decode_payloads_at_path(decoded_event, path)
    
    return decoded_event


def _decode_payloads_at_path(event: dict, path: list) -> None:
    """Decode payloads at a specific path in the event structure."""
    current = event
    
    # Navigate to the target location
    for key in path[:-1]:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return  # Path doesn't exist
    
    # Check if final key exists and contains payloads
    final_key = path[-1]
    if isinstance(current, dict) and final_key in current:
        payloads = current[final_key]
        if isinstance(payloads, list):
            # Decode each payload in the list
            for payload in payloads:
                if isinstance(payload, dict):
                    _decode_single_payload(payload)


def _decode_single_payload(payload: dict) -> None:
    """Decode a single payload object with data and metadata fields."""
    # Decode data field
    if "data" in payload and isinstance(payload["data"], str):
        try:
            # Decode base64
            decoded_bytes = base64.b64decode(payload["data"])
            # Try to parse as JSON
            try:
                decoded_json = json.loads(decoded_bytes.decode('utf-8'))
                payload["data"] = decoded_json
            except (json.JSONDecodeError, UnicodeDecodeError):
                # If not JSON, store as string
                try:
                    payload["data"] = _truncate_string_if_needed(decoded_bytes.decode('utf-8'))
                except UnicodeDecodeError:
                    payload["data"] = f"<binary data: {len(decoded_bytes)} bytes>"
        except Exception:
            # If decoding fails, silently continue
            pass
    
    # Decode metadata field
    if "metadata" in payload and isinstance(payload["metadata"], dict):
        # Store decoded values temporarily to avoid modifying dict during iteration
        decoded_metadata = {}
        for key, value in payload["metadata"].items():
            if isinstance(value, str):
                try:
                    # Decode base64
                    decoded_bytes = base64.b64decode(value)
                    try:
                        decoded_json = json.loads(decoded_bytes.decode('utf-8'))
                        decoded_metadata[key] = decoded_json
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        try:
                            decoded_metadata[key] = _truncate_string_if_needed(decoded_bytes.decode('utf-8'))
                        except UnicodeDecodeError:
                            decoded_metadata[key] = f"<binary data: {len(decoded_bytes)} bytes>"
                except Exception:
                    # If decoding fails, keep original value
                    decoded_metadata[key] = value
            else:
                # Keep non-string values as-is
                decoded_metadata[key] = value
        
        # Update the metadata dictionary after iteration is complete
        payload["metadata"] = decoded_metadata
