"""
Utility functions for workflow search fallback logic.
"""
import re
from typing import Dict, Any, Optional, Tuple


def has_empty_results(result: Dict[str, Any]) -> bool:
    """Check if a workflow search result is empty.
    
    Args:
        result: Result from temporal workflow command
        
    Returns:
        True if the result contains no workflows
    """
    if not result.get("success", False):
        return False
    
    # For list commands, check if data array is empty
    if "data" in result:
        data = result["data"]
        if isinstance(data, list):
            return len(data) == 0
        # For count commands, check if count is 0
        elif isinstance(data, dict) and "count" in data:
            return data["count"] == "0" or data["count"] == 0
    
    return False


def extract_workflow_name_from_query(query: str) -> Optional[str]:
    """Extract a potential workflow name from a Temporal query string.
    
    Looks for patterns like:
    - WorkflowType = 'name'
    - WorkflowType='name'
    - WorkflowType STARTS_WITH 'name'
    
    Args:
        query: Temporal query string
        
    Returns:
        Extracted workflow name or None
    """
    if not query:
        return None
    
    # Pattern to match WorkflowType queries
    patterns = [
        r"WorkflowType\s*=\s*['\"]([^'\"]+)['\"]",
        r"WorkflowType\s+STARTS_WITH\s+['\"]([^'\"]+)['\"]",
        r"WorkflowType\s+CONTAINS\s+['\"]([^'\"]+)['\"]"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def create_workflowid_fallback_query(workflow_name: str, original_query: Optional[str] = None) -> str:
    """Create a WorkflowId STARTS_WITH fallback query.
    
    Args:
        workflow_name: The workflow name to search for as prefix
        original_query: Original query to preserve other conditions
        
    Returns:
        New query string using WorkflowId STARTS_WITH
    """
    fallback_condition = f"WorkflowId STARTS_WITH '{workflow_name}'"
    
    if not original_query:
        return fallback_condition
    
    # Try to preserve other conditions from original query
    # Remove the WorkflowType condition and replace with WorkflowId
    modified_query = re.sub(
        r"WorkflowType\s*(?:=|STARTS_WITH|CONTAINS)\s*['\"][^'\"]+['\"]",
        fallback_condition,
        original_query,
        flags=re.IGNORECASE
    )
    
    # If no substitution was made, add the condition
    if modified_query == original_query:
        if "AND" in original_query.upper() or "OR" in original_query.upper():
            modified_query = f"({fallback_condition}) AND ({original_query})"
        else:
            modified_query = f"{fallback_condition} AND {original_query}"
    
    return modified_query


async def try_workflowid_fallback(
    original_result: Dict[str, Any],
    original_query: Optional[str],
    executor_func,
    limit: Optional[int] = None
) -> Tuple[Dict[str, Any], bool]:
    """Try WorkflowId fallback if original query returned empty results.
    
    Args:
        original_result: Result from original query
        original_query: Original query string
        executor_func: Function to execute the fallback query
        limit: Optional limit for the query
        
    Returns:
        Tuple of (result, fallback_used)
    """
    # If original query succeeded and has results, return as-is
    if not has_empty_results(original_result):
        return original_result, False
    
    # Try to extract workflow name for fallback
    workflow_name = extract_workflow_name_from_query(original_query) if original_query else None
    if not workflow_name:
        return original_result, False
    
    # Create fallback query
    fallback_query = create_workflowid_fallback_query(workflow_name, original_query)
    
    try:
        # Execute fallback query
        if limit is not None:
            fallback_result = await executor_func(fallback_query, limit)
        else:
            fallback_result = await executor_func(fallback_query)
        
        # Add metadata about fallback usage
        if fallback_result.get("success", False):
            fallback_result["fallback_used"] = True
            fallback_result["original_query"] = original_query
            fallback_result["fallback_query"] = fallback_query
            fallback_result["fallback_reason"] = f"WorkflowType '{workflow_name}' not found, tried WorkflowId prefix instead"
            
            return fallback_result, True
    except Exception:
        # If fallback fails, return original result
        pass
    
    return original_result, False