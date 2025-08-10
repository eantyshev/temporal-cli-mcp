from typing import Any, Dict

from ..core import mcp, run_temporal_command


@mcp.tool()
async def get_workflow_history(
    workflow_id: str,
    follow: bool = False,
) -> Dict[str, Any]:
    args = ["workflow", "show", "--workflow-id", workflow_id]
    if follow:
        args.append("--follow")
    result = await run_temporal_command(args, output="json")
    return result
