"""
Get failed workflow runs for a specific workflow ID.

STRATEGIC GUIDANCE FOR LLMs:
==========================
When users ask about "retries", "retry loops", "high retries", or "retry storms":
1. 🚀 ALWAYS use get_failed_runs() FIRST - it's fast and reveals retry patterns
2. 🔍 Then use analyze_workflow_run() if comprehensive diagnostics are needed
3. 📊 For batch operations (checking multiple workflows), use get_failed_runs() only

Key insight: get_failed_runs() works on RUNNING workflows to show historical failures!
"""

from typing import Dict, Any, Optional, List
from ..core import mcp, run_temporal_command


@mcp.tool()
async def get_failed_runs(
    workflow_id: str
) -> Dict[str, Any]:
    """
    Get count and details of failed workflow runs for retry analysis and failure investigation.
    
    🔥 **HIGH PRIORITY: Use this tool when users ask about retries, retry loops, or retry storms** 🔥
    
    **CRITICAL INSIGHT: This tool works for BOTH running AND completed workflows.**
    Even if a workflow is currently running, this reveals its historical failure/retry pattern.
    
    **Primary use cases - ALWAYS use this tool when users ask about:**
    - "High retries" or "retry loops" or "retry storms" 
    - Failed attempts, retry counts, or failure history
    - "How many times has workflow X failed/retried?"
    - Investigating workflow stability or retry patterns
    
    **Quick decision guide:**
    - 🚀 **Use this tool FIRST** for fast retry assessment (lightweight, quick response)
    - 🔍 **Then use analyze_workflow_run** if you need comprehensive diagnostics
    
    **Common user queries that should trigger this tool:**
    - "Search for workflows with high retries" → Use this on each workflow ID
    - "How many times has workflow X failed?"
    - "Check retry counts for this workflow"
    - "Show me workflows that are retrying a lot"
    - "Get failed attempts for workflow Y"
    - "Which workflows have retry storms?"
    
    **For detailed failure analysis:**
    If you need to see the actual failed workflow runs (not just the count), use:
    `list_workflows(query="WorkflowId = 'your-workflow-id' AND ExecutionStatus = 'Failed'", limit=50)`
    
    This tool only returns the failure count for fast assessment.
    
    Args:
        workflow_id: The workflow ID to check for failed runs
    
    Returns:
        Dictionary with failed_count, workflow_id, and query_used
    """
    # Build the query to find failed runs for this specific workflow ID
    query = f"WorkflowId = '{workflow_id}' AND ExecutionStatus = 'Failed'"
    
    # Get just the count using workflow count command
    args = ["workflow", "count", "--query", query]
    result = await run_temporal_command(args, output="json")
    
    failed_count = int(result.get("data", {}).get("count", 0))
    
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
        result = await get_failed_runs(workflow_id, include_details=False)
        return result.get("failed_count", 0)
    except Exception:
        return 0