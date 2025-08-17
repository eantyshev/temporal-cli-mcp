from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def reset_workflow(
    workflow_id: Optional[str] = None,
    event_id: Optional[str] = None,
    reason: Optional[str] = None,
    run_id: Optional[str] = None,
    query: Optional[str] = None,
    reset_type: Optional[str] = None,
    build_id: Optional[str] = None,
    reapply_exclude: Optional[str] = None,
    yes: bool = False,
) -> Dict[str, Any]:
    """Reset a Workflow Execution to a previous point in its Event History.
    
    Supports both single workflow reset and batch operations via visibility queries.
    
    For batch resets, limit your resets to FirstWorkflowTask, LastWorkflowTask, or
    BuildId reset types. Do not use Workflow IDs, run IDs, or event IDs with batch operations.
    
    Note: Temporal CLI does not provide a --dry-run option for reset operations.
    
    Args:
        workflow_id: The Workflow ID to reset (required for single workflow reset)
        event_id: Optional event ID to reset to. If not provided, resets to last continued-as-new or retry event
        reason: Optional reason for the reset (required for batch operations)
        run_id: Optional specific run ID to target (not allowed for batch operations)
        query: Visibility query for batch operations (SQL-like query to select workflows)
        reset_type: Reset type - FirstWorkflowTask, LastWorkflowTask, LastContinuedAsNew, or BuildId
        build_id: Build ID for BuildId reset type. Build IDs identify worker code versions.
            BuildId reset resets workflows to the first task processed by a specific build,
            useful for rolling back after bad deployments or code regressions
        reapply_exclude: Exclude event types from re-application. When resetting, Temporal 
            normally re-applies events that occurred after the reset point. This parameter 
            excludes specific event types: 'All' (exclude all events for clean reset), 
            'Signal' (exclude signal events that may no longer be relevant), 'Update' 
            (exclude workflow updates that shouldn't be re-applied)
        yes: Skip confirmation for batch operations (only allowed with query)
        
    Returns:
        Dictionary with reset operation results
    """
    # Validation for batch vs single workflow operations
    is_batch_operation = query is not None
    
    if is_batch_operation:
        # Batch operation validations
        if workflow_id or run_id or event_id:
            raise ValueError("Batch operations (using --query) cannot use workflow_id, run_id, or event_id")
        
        if not reason:
            raise ValueError("Batch operations require a reason")
            
        if reset_type not in ["FirstWorkflowTask", "LastWorkflowTask", "BuildId"]:
            raise ValueError("Batch operations must use reset_type: FirstWorkflowTask, LastWorkflowTask, or BuildId")
            
        if reset_type == "BuildId" and not build_id:
            raise ValueError("BuildId reset type requires build_id parameter")
    else:
        # Single workflow operation validations
        if not workflow_id:
            raise ValueError("Single workflow reset requires workflow_id")
            
        if yes:
            raise ValueError("--yes flag is only allowed for batch operations (with --query)")

    args = ["workflow", "reset"]
    
    # Add workflow-specific parameters for single workflow reset
    if workflow_id:
        args.extend(["--workflow-id", workflow_id])
    
    if event_id:
        args.extend(["--event-id", event_id])
        
    if run_id:
        args.extend(["--run-id", run_id])
    
    # Add batch operation parameters
    if query:
        args.extend(["--query", query])
        
    if reset_type:
        args.extend(["--type", reset_type])
        
    if build_id:
        args.extend(["--build-id", build_id])
    
    # Add common parameters
    if reason:
        args.extend(["--reason", reason])
        
    if reapply_exclude:
        args.extend(["--reapply-exclude", reapply_exclude])
        
    if yes:
        args.append("--yes")
    
    result = await run_temporal_command(args, output="json")
    return result