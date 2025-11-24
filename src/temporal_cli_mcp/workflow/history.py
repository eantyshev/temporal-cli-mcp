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


# ============================================================================
# Filtering Helper Functions
# ============================================================================

def _filter_by_event_types(events: list, event_types: list[str]) -> list:
    """Filter events by exact event type match."""
    if not event_types:
        return events
    return [e for e in events if isinstance(e, dict) and e.get("eventType") in event_types]


def _exclude_event_types(events: list, exclude_types: list[str]) -> list:
    """Exclude specific event types."""
    if not exclude_types:
        return events
    return [e for e in events if isinstance(e, dict) and e.get("eventType") not in exclude_types]


def _filter_by_event_id_range(events: list, start_id: Optional[int], end_id: Optional[int]) -> list:
    """Filter events by event ID range (inclusive)."""
    if start_id is None and end_id is None:
        return events
    
    filtered = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = event.get("eventId")
        if not isinstance(event_id, (int, str)):
            continue
        
        try:
            event_id_int = int(event_id)
            if start_id is not None and event_id_int < start_id:
                continue
            if end_id is not None and event_id_int > end_id:
                continue
            filtered.append(event)
        except (ValueError, TypeError):
            continue
    
    return filtered


def _apply_field_projection(events: list, level: str) -> list:
    """Apply field projection to reduce event size.
    
    Args:
        events: List of event dictionaries
        level: "minimal", "standard", or "full"
    
    Returns:
        List of events with projected fields
    """
    if level == "full":
        return events
    
    projected_events = []
    for event in events:
        if not isinstance(event, dict):
            projected_events.append(event)
            continue
        
        # Minimal: eventId, eventType, eventTime only
        projected = {
            "eventId": event.get("eventId"),
            "eventType": event.get("eventType"),
            "eventTime": event.get("eventTime"),
        }
        
        # Standard: add failure messages and key identifiers
        if level == "standard":
            event_type = event.get("eventType", "")
            
            # Add failure-related fields
            if "Failed" in event_type or "TimedOut" in event_type or "Terminated" in event_type:
                for key in event.keys():
                    if "EventAttributes" in key:
                        attrs = event[key]
                        if isinstance(attrs, dict):
                            # Include failure/timeout/termination details
                            if "failure" in attrs:
                                projected.setdefault(key, {})["failure"] = attrs["failure"]
                            if "timeoutType" in attrs:
                                projected.setdefault(key, {})["timeoutType"] = attrs["timeoutType"]
                            if "reason" in attrs:
                                projected.setdefault(key, {})["reason"] = attrs["reason"]
                            if "cause" in attrs:
                                projected.setdefault(key, {})["cause"] = attrs["cause"]
            
            # Add key identifiers for correlation
            for key in event.keys():
                if "EventAttributes" in key:
                    attrs = event[key]
                    if isinstance(attrs, dict):
                        # Activity identifiers
                        if "activityId" in attrs:
                            projected.setdefault(key, {})["activityId"] = attrs["activityId"]
                        if "activityType" in attrs:
                            projected.setdefault(key, {})["activityType"] = attrs["activityType"]
                        # Timer identifiers
                        if "timerId" in attrs:
                            projected.setdefault(key, {})["timerId"] = attrs["timerId"]
                        # Child workflow identifiers
                        if "workflowId" in attrs:
                            projected.setdefault(key, {})["workflowId"] = attrs["workflowId"]
                        if "workflowType" in attrs:
                            projected.setdefault(key, {})["workflowType"] = attrs["workflowType"]
                        # Signal identifiers
                        if "signalName" in attrs:
                            projected.setdefault(key, {})["signalName"] = attrs["signalName"]
        
        projected_events.append(projected)
    
    return projected_events


def _apply_preset(events: list, preset: str) -> tuple[list, list[str]]:
    """Apply a smart preset filter to events.
    
    Args:
        events: List of event dictionaries
        preset: Preset name ("last_failure_context", "resets", "summary", "critical_path")
    
    Returns:
        Tuple of (filtered_events, list of filter descriptions applied)
    """
    filters_applied = [f"preset={preset}"]
    
    if preset == "last_failure_context":
        # Find last failure event
        failure_types = [
            "WORKFLOW_TASK_FAILED",
            "ACTIVITY_TASK_FAILED",
            "CHILD_WORKFLOW_EXECUTION_FAILED",
            "WORKFLOW_EXECUTION_FAILED",
        ]
        last_failure_idx = None
        for i in range(len(events) - 1, -1, -1):
            if isinstance(events[i], dict) and events[i].get("eventType") in failure_types:
                last_failure_idx = i
                break
        
        if last_failure_idx is not None:
            # Return last failure + 10 events before it
            start_idx = max(0, last_failure_idx - 10)
            return events[start_idx:last_failure_idx + 1], filters_applied
        else:
            # No failures found, return empty
            return [], filters_applied
    
    elif preset == "resets":
        # All WORKFLOW_TASK_FAILED events (typically include resets)
        filtered = [e for e in events if isinstance(e, dict) and e.get("eventType") == "WORKFLOW_TASK_FAILED"]
        return filtered, filters_applied
    
    elif preset == "summary":
        # Key state transitions only
        summary_types = [
            "WORKFLOW_EXECUTION_STARTED",
            "WORKFLOW_EXECUTION_COMPLETED",
            "WORKFLOW_EXECUTION_FAILED",
            "WORKFLOW_EXECUTION_CANCELED",
            "WORKFLOW_EXECUTION_TIMED_OUT",
            "WORKFLOW_EXECUTION_CONTINUED_AS_NEW",
            "WORKFLOW_EXECUTION_TERMINATED",
            "CHILD_WORKFLOW_EXECUTION_STARTED",
            "CHILD_WORKFLOW_EXECUTION_COMPLETED",
            "CHILD_WORKFLOW_EXECUTION_FAILED",
            "ACTIVITY_TASK_STARTED",
            "ACTIVITY_TASK_COMPLETED",
            "ACTIVITY_TASK_FAILED",
        ]
        filtered = [e for e in events if isinstance(e, dict) and e.get("eventType") in summary_types]
        return filtered, filters_applied
    
    elif preset == "critical_path":
        # Exclude verbose events
        verbose_types = [
            "TIMER_FIRED",
            "TIMER_STARTED",
            "TIMER_CANCELED",
            "MARKER_RECORDED",
            "UPSERT_WORKFLOW_SEARCH_ATTRIBUTES",
            "WORKFLOW_PROPERTIES_MODIFIED",
        ]
        filtered = [e for e in events if isinstance(e, dict) and e.get("eventType") not in verbose_types]
        return filtered, filters_applied
    
    else:
        # Unknown preset, return all events
        return events, [f"preset={preset} (unknown, no filtering applied)"]


@mcp.tool()
async def get_workflow_history(
    workflow_id: str,
    run_id: Optional[str] = None,
    decode_payloads: bool = True,
    # Filtering parameters
    event_types: Optional[list[str]] = None,
    exclude_event_types: Optional[list[str]] = None,
    limit: Optional[int] = None,
    reverse: bool = False,
    start_event_id: Optional[int] = None,
    end_event_id: Optional[int] = None,
    # Field projection
    fields: str = "full",
    # Smart presets
    preset: Optional[str] = None,
) -> Dict[str, Any]:
    """Get workflow execution history with automatic base64 payload decoding and filtering.
    
    This tool retrieves the complete event history for a workflow execution,
    with optional post-processing filters to reduce response size for large histories.
    
    NOTE: All filtering is done via post-processing AFTER fetching the full history from
    Temporal CLI. This means filtering doesn't improve performance for fetching, but 
    significantly reduces token usage in responses.
    
    Args:
        workflow_id: The workflow ID to retrieve history for
        run_id: Optional specific run ID to target
        decode_payloads: Whether to automatically decode base64 payloads (default: True)
        
        # Filtering parameters
        event_types: Filter to specific event types (exact matches, e.g., ["WORKFLOW_TASK_FAILED"])
        exclude_event_types: Exclude specific event types (e.g., ["TIMER_FIRED"])
        limit: Maximum number of events to return after filtering
        reverse: Return events in reverse chronological order (most recent first)
        start_event_id: Start from this event ID (inclusive)
        end_event_id: End at this event ID (inclusive)
        
        # Field projection (reduces response size)
        fields: Field projection level:
            - "minimal": eventId, eventType, eventTime only
            - "standard": minimal + failure messages, state transitions, key identifiers
            - "full": all fields including payloads (default)
        
        # Smart presets (override other filter params)
        preset: Smart preset filter:
            - "last_failure_context": Last failure event + 10 events before it
            - "resets": All WORKFLOW_TASK_FAILED events
            - "summary": Key state transitions only (Started, Completed, Failed, etc.)
            - "critical_path": Exclude verbose events (timers, markers, etc.)
    
    Returns:
        Dict with workflow history. If filtering is applied, includes "filter_info" with:
        - original_event_count: Number of events before filtering
        - filtered_event_count: Number of events after filtering
        - filters_applied: List of filters that were applied
    
    Example:
        # Most common debugging use case (reduces 45KB to ~2KB)
        get_workflow_history(
            workflow_id="megaflow-xyz",
            reverse=True,
            limit=30,
            event_types=["WORKFLOW_TASK_FAILED", "WORKFLOW_TASK_COMPLETED"],
            fields="standard"
        )
        
        # Quick failure analysis
        get_workflow_history(workflow_id="megaflow-xyz", preset="last_failure_context")
        
        # Critical path only
        get_workflow_history(workflow_id="megaflow-xyz", preset="critical_path", fields="minimal")
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
        
        # Track original event count for filter_info
        original_event_count = len(result.get("events", []))
        
        # Step 1: Decode payloads if requested
        events = result.get("events", [])
        if request.decode_payloads and events:
            events = _decode_event_payloads(events)
        
        # Step 2: Apply filtering if any filter params are provided
        filters_applied = []
        
        # Check if any filtering is needed
        needs_filtering = (
            preset is not None
            or event_types is not None
            or exclude_event_types is not None
            or limit is not None
            or reverse
            or start_event_id is not None
            or end_event_id is not None
            or fields != "full"
        )
        
        if needs_filtering and events:
            # Apply preset first (overrides other filters except fields)
            if preset:
                events, preset_filters = _apply_preset(events, preset)
                filters_applied.extend(preset_filters)
            else:
                # Apply individual filters in order
                if event_types:
                    events = _filter_by_event_types(events, event_types)
                    filters_applied.append(f"event_types={event_types}")
                
                if exclude_event_types:
                    events = _exclude_event_types(events, exclude_event_types)
                    filters_applied.append(f"exclude_event_types={exclude_event_types}")
                
                if start_event_id is not None or end_event_id is not None:
                    events = _filter_by_event_id_range(events, start_event_id, end_event_id)
                    filters_applied.append(f"event_id_range=[{start_event_id or 'start'}:{end_event_id or 'end'}]")
            
            # Apply reverse and limit (applies to both preset and manual filters)
            if reverse:
                events = list(reversed(events))
                filters_applied.append("reverse=True")
            
            if limit is not None:
                events = events[:limit]
                filters_applied.append(f"limit={limit}")
            
            # Apply field projection last
            if fields != "full":
                events = _apply_field_projection(events, fields)
                filters_applied.append(f"fields={fields}")
        
        # Build result with filter info
        new_result = dict(result)
        new_result["events"] = events
        
        # Add filter_info if filtering was applied
        if filters_applied:
            new_result["filter_info"] = {
                "original_event_count": original_event_count,
                "filtered_event_count": len(events),
                "filters_applied": filters_applied,
            }
        
        # WORKAROUND: Sanitize the result to avoid FastMCP's dictionary iteration bug
        return _sanitize_for_fastmcp(new_result)
        
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
