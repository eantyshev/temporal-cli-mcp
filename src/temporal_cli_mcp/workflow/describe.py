from typing import Any, Dict

from ..core import mcp, run_temporal_command


@mcp.tool()
async def describe_workflow(
    workflow_id: str,
) -> Dict[str, Any]:
    args = ["workflow", "describe", "--workflow-id", workflow_id]
    result = await run_temporal_command(args, output="json")
    return result
