from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def count_workflows(
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """Count Workflow Executions matching the given query.
    
    This tool is useful for checking how many workflows match a query
    before listing them to avoid token-heavy responses. Use this tool
    before list_workflows when you expect many results to get an overview
    of the result size and optimize token usage.
    
    Best Practice: Always call count_workflows before list_workflows when:
    - Exploring workflows without knowing the result size
    - Working with broad query filters
    - Analyzing workflow patterns across large datasets
    
    Smart Fallback: If a WorkflowType query returns zero results, automatically
    retries using the workflow name as a WorkflowId prefix pattern.
    Example: WorkflowType = 'megaflow' → WorkflowId STARTS_WITH 'megaflow'
    
    Args:
        query: Optional query filter to count specific workflows
        
    Returns:
        Dictionary with count information and query details
    """
    args = ["workflow", "count"]
    if query:
        args.extend(["--query", query])
    
    result = await run_temporal_command(args, output="json")
    
    # Try WorkflowId fallback if no results found
    from ..workflow_fallback import try_workflowid_fallback
    
    async def executor_func(fallback_query: str) -> Dict[str, Any]:
        fallback_args = ["workflow", "count", "--query", fallback_query]
        return await run_temporal_command(fallback_args, output="json")
    
    result, fallback_used = await try_workflowid_fallback(
        result, query, executor_func
    )
    
    return result