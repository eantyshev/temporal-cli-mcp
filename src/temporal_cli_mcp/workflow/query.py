from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def query_workflow(
    workflow_id: str,
    query_type: str,
    input_data: Optional[str] = None,
) -> Dict[str, Any]:
    args = ["workflow", "query", "--workflow-id", workflow_id, "--type", query_type]
    if input_data:
        args.extend(["--input", input_data])
    result = await run_temporal_command(args, output="json")
    return result
