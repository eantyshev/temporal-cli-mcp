from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def terminate_workflow(
    workflow_id: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    args = ["workflow", "terminate", "--workflow-id", workflow_id]
    if reason:
        args.extend(["--reason", reason])
    result = await run_temporal_command(args, output="json")
    return result
