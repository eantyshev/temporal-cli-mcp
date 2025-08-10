from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def list_workflows(
    query: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """List workflows with input validation and improved error handling."""
    from ..models import WorkflowListRequest
    from ..base import AsyncCommandExecutor, WorkflowCommandHandler
    from ..command_builder import TemporalCommandBuilder
    from ..config import config
    from ..exceptions import ValidationError
    
    try:
        # Validate input
        request = WorkflowListRequest(query=query, limit=limit)
        
        # Create executor and builder
        executor = AsyncCommandExecutor()
        builder = TemporalCommandBuilder(env=config.env)
        
        # Build and execute command
        workflow_args = builder.build_workflow_list(request.query, request.limit)
        cmd = builder.build_full_command(workflow_args)
        result = await executor.execute(cmd)
        
        if not result["success"]:
            raise Exception(f"Failed to list workflows: {result['stderr']}")
        
        return result
        
    except Exception as e:
        if "ValidationError" in str(type(e)):
            raise ValidationError(f"Invalid input: {e}")
        raise
