from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def reset_workflow(
    workflow_id: str,
    event_id: Optional[str] = None,
    reason: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Reset a Workflow Execution to a previous point in its Event History.
    
    Args:
        workflow_id: The Workflow ID to reset
        event_id: Optional event ID to reset to. If not provided, resets to last continued-as-new or retry event
        reason: Optional reason for the reset
        run_id: Optional specific run ID to target
        
    Returns:
        Dictionary with reset operation results
    """
    args = ["workflow", "reset", "--workflow-id", workflow_id]
    
    if event_id:
        args.extend(["--event-id", event_id])
    
    if reason:
        args.extend(["--reason", reason])
        
    if run_id:
        args.extend(["--run-id", run_id])
    
    result = await run_temporal_command(args, output="json")
    return result