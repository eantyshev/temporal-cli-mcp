from typing import Any, Dict, Optional

from ..core import mcp


@mcp.tool()
async def trace_workflow(
    workflow_id: str,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get workflow stack trace for a running workflow.
    
    This tool retrieves the current stack trace/goroutine information for a running workflow,
    which is useful for debugging stuck or long-running workflows to see exactly where
    they are blocked or what they are waiting for.
    
    Args:
        workflow_id: The workflow ID to get stack trace for
        run_id: Optional specific run ID to target
    """
    from ..models import WorkflowStackRequest
    from ..base import AsyncCommandExecutor
    from ..command_builder import TemporalCommandBuilder
    from ..config import config
    from ..exceptions import ValidationError
    
    try:
        # Validate input
        request = WorkflowStackRequest(
            workflow_id=workflow_id,
            run_id=run_id
        )
        
        # Create executor and builder
        executor = AsyncCommandExecutor()
        builder = TemporalCommandBuilder(env=config.env)
        
        # Build and execute command
        workflow_args = builder.build_workflow_stack(request.workflow_id, request.run_id)
        cmd = builder.build_full_command(workflow_args)
        result = await executor.execute(cmd)
        
        if not result["success"]:
            raise Exception(f"Failed to get workflow stack: {result['stderr']}")
        
        return result
        
    except Exception as e:
        if "ValidationError" in str(type(e)):
            raise ValidationError(f"Invalid input: {e}")
        raise