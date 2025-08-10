from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def signal_workflow(
    workflow_id: str,
    signal_name: str,
    input_data: Optional[str] = None,
) -> Dict[str, Any]:
    args = ["workflow", "signal", "--workflow-id", workflow_id, "--name", signal_name]
    if input_data:
        args.extend(["--input", input_data])
    result = await run_temporal_command(args, output="json")
    return result
