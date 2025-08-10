from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def start_workflow(
    workflow_type: str,
    task_queue: str,
    workflow_id: Optional[str] = None,
    input_data: Optional[str] = None,
) -> Dict[str, Any]:
    args = ["workflow", "start", "--type", workflow_type, "--task-queue", task_queue]
    if workflow_id:
        args.extend(["--workflow-id", workflow_id])
    if input_data:
        args.extend(["--input", input_data])
    result = await run_temporal_command(args, output="json")
    return result
