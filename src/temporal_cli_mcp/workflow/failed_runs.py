"""
Lightweight helper to get the number of failed runs for a workflow.

Notes:
- Works for both running and completed workflows (historical failures are counted).
- Returns just the count for quick retry assessment; use analysis tools for deep dives.
"""

from typing import Dict, Any
from ..core import mcp, run_temporal_command


async def _failed_runs_count_and_query(workflow_id: str) -> tuple[int, str]:
    """Internal helper to compute failed runs count and the query used."""
    query = f"WorkflowId = '{workflow_id}' AND ExecutionStatus = 'Failed'"
    args = ["workflow", "count", "--query", query]
    result = await run_temporal_command(args, output="json")
    count = int(result.get("data", {}).get("count", 0))
    return count, query

@mcp.tool()
async def get_failed_runs(
    workflow_id: str
) -> Dict[str, Any]:
    """
    Get the count of failed workflow runs for a given workflow ID.

    For details beyond the count (e.g., full listings or diagnostics), prefer the
    guide and analysis tools in this package.

    Args:
        workflow_id: The workflow ID to check for failed runs
    
    Returns:
        Dictionary with keys: success, workflow_id, failed_count, query_used
    """
    failed_count, query = await _failed_runs_count_and_query(workflow_id)
    
    return {
        "success": True,
        "workflow_id": workflow_id,
        "failed_count": failed_count,
        "query_used": query
    }


async def get_failed_runs_count_only(workflow_id: str) -> int:
    """
    Helper function to get just the count of failed runs for a workflow.
    
    Args:
        workflow_id: The workflow ID to check
        
    Returns:
        Number of failed runs (0 if error occurs)
    """
    try:
        count, _query = await _failed_runs_count_and_query(workflow_id)
        return count
    except Exception:
        return 0