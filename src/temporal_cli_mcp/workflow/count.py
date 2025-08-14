from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def count_workflows(
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """Count Workflow Executions matching the given query.
    
    This tool is useful for checking how many workflows match a query
    before listing them to avoid token-heavy responses.
    
    Args:
        query: Optional query filter to count specific workflows
        
    Returns:
        Dictionary with count information and query details
    """
    args = ["workflow", "count"]
    if query:
        args.extend(["--query", query])
    
    result = await run_temporal_command(args, output="json")
    return result