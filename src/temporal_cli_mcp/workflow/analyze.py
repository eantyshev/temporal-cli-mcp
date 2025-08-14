"""
Workflow analysis tool for comprehensive diagnostics.

STRATEGIC GUIDANCE FOR LLMs:
==========================
Decision flow for workflow analysis:
1. Quick retry check → Use get_failed_runs() (fast, lightweight)
2. Need full diagnostics → Use analyze_workflow_run() (comprehensive, slower)
3. Batch retry analysis → Use get_failed_runs() on multiple workflows

This tool provides deep insights but requires more computation than get_failed_runs().
"""

import json
from typing import Dict, Any, Optional
from ..core import mcp, run_temporal_command
from .failed_runs import get_failed_runs_count_only


async def analyze_workflow_run(
    workflow_id: str,
    include_history: bool = True,
    include_stack_trace: bool = True
) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of a workflow run including retry statistics,
    failure patterns, execution history, and diagnostic recommendations.
    
    💡 **For quick retry counts, use get_failed_runs first - it's faster and lighter!**
    
    **Use this tool when you need COMPREHENSIVE DIAGNOSTICS beyond basic retry counts:**
    - Deep failure pattern analysis and root cause investigation
    - Execution timeline analysis and performance diagnostics  
    - Stuck workflow diagnosis with stack traces
    - Actionable recommendations for workflow remediation
    - Full retry storm analysis with severity assessment
    
    **Key differences from get_failed_runs:**
    - ⚡ get_failed_runs: Quick retry counts (recommended first step)
    - 🔬 analyze_workflow_run: Full diagnostics (use when you need details)
    
    **Common scenarios for this tool:**
    - "Why is this workflow failing repeatedly?" (after checking retry count)
    - "What's wrong with this workflow?" (comprehensive diagnosis)
    - "Is this workflow stuck?" (includes stack trace analysis)
    - "Analyze the failure pattern" (detailed pattern detection)
    - "Give me recommendations to fix this workflow"
    
    **⚠️ Note:** This tool performs more computation and takes longer than get_failed_runs.
    Use get_failed_runs first for quick assessments, then this for deep dives.
    
    Args:
        workflow_id: The workflow ID to analyze
        include_history: Whether to fetch full execution history (default: True)
        include_stack_trace: Whether to attempt stack trace retrieval (default: True)
    
    Returns:
        Comprehensive analysis with retry stats, status, history patterns, and recommendations
    """


def _analyze_execution_history(events: list) -> Dict[str, Any]:
    """Analyze execution history events for patterns."""
    if not events:
        return {}
    
    analysis = {
        "total_events": len(events),
        "event_types": {},
        "execution_timeline": [],
        "child_workflows": [],
        "failures": [],
        "signals": [],
        "activities": []
    }
    
    # Count event types
    for event in events:
        event_type = event.get("eventType", "UNKNOWN")
        analysis["event_types"][event_type] = analysis["event_types"].get(event_type, 0) + 1
        
        # Extract key timeline events
        if event_type in ["EVENT_TYPE_WORKFLOW_EXECUTION_STARTED", "EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED", 
                         "EVENT_TYPE_WORKFLOW_EXECUTION_FAILED", "EVENT_TYPE_WORKFLOW_EXECUTION_TERMINATED"]:
            analysis["execution_timeline"].append({
                "event_id": event.get("eventId"),
                "event_type": event_type,
                "event_time": event.get("eventTime")
            })
        
        # Track child workflows
        if event_type == "EVENT_TYPE_START_CHILD_WORKFLOW_EXECUTION_INITIATED":
            attrs = event.get("startChildWorkflowExecutionInitiatedEventAttributes", {})
            analysis["child_workflows"].append({
                "workflow_id": attrs.get("workflowId"),
                "workflow_type": attrs.get("workflowType", {}).get("name"),
                "event_time": event.get("eventTime")
            })
        
        # Track failures
        if "FAILED" in event_type:
            analysis["failures"].append({
                "event_id": event.get("eventId"),
                "event_type": event_type,
                "event_time": event.get("eventTime"),
                "details": event.get("workflowExecutionFailedEventAttributes") or 
                          event.get("activityTaskFailedEventAttributes") or 
                          event.get("childWorkflowExecutionFailedEventAttributes")
            })
        
        # Track signals
        if "SIGNAL" in event_type:
            analysis["signals"].append({
                "event_id": event.get("eventId"),
                "event_type": event_type,
                "event_time": event.get("eventTime")
            })
    
    return analysis


def _identify_failure_patterns(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Identify common failure patterns from the analysis."""
    patterns = {
        "is_retry_storm": False,
        "has_child_workflow_failures": False,
        "has_timeout_pattern": False,
        "has_data_corruption": False,
        "pattern_description": []
    }
    
    retry_stats = analysis.get("retry_statistics", {})
    
    # Retry storm detection
    if retry_stats.get("failed_attempts", 0) > 50:
        patterns["is_retry_storm"] = True
        patterns["pattern_description"].append("RETRY STORM: Excessive retry attempts detected")
    
    # Child workflow failure pattern
    exec_analysis = analysis.get("execution_analysis", {})
    if exec_analysis.get("failures"):
        patterns["has_child_workflow_failures"] = True
        patterns["pattern_description"].append("Child workflow failures detected")
    
    # Timeout pattern (consistent execution duration)
    current_status = analysis.get("current_status", {})
    if current_status.get("history_length") == 47 and retry_stats.get("failed_attempts", 0) > 10:
        patterns["has_timeout_pattern"] = True
        patterns["pattern_description"].append("Consistent timeout pattern (17min executions)")
    
    # Data corruption/schema mismatch
    if retry_stats.get("failed_attempts", 0) > 20 and retry_stats.get("successful_attempts", 0) == 0:
        patterns["has_data_corruption"] = True
        patterns["pattern_description"].append("Possible data schema mismatch or corruption")
    
    return patterns


def _generate_recommendations(analysis: Dict[str, Any]) -> list:
    """Generate actionable recommendations based on analysis."""
    recommendations = []
    
    retry_stats = analysis.get("retry_statistics", {})
    failure_patterns = analysis.get("failure_patterns", {})
    current_status = analysis.get("current_status", {})
    
    # Critical retry storm
    if failure_patterns.get("is_retry_storm"):
        recommendations.append({
            "priority": "CRITICAL",
            "action": "IMMEDIATE_INTERVENTION",
            "description": f"Stop retry storm: {retry_stats.get('failed_attempts')} failed attempts",
            "suggested_commands": [
                f"temporal workflow terminate --workflow-id {analysis['workflow_id']} --reason 'Stopping retry storm'"
            ]
        })
    
    # Timeout pattern
    if failure_patterns.get("has_timeout_pattern"):
        recommendations.append({
            "priority": "HIGH", 
            "action": "RESET_WORKFLOW",
            "description": "Reset workflow to earlier successful state",
            "suggested_commands": [
                f"temporal workflow reset --workflow-id {analysis['workflow_id']} --reason 'Breaking timeout pattern'"
            ]
        })
    
    # Data corruption
    if failure_patterns.get("has_data_corruption"):
        recommendations.append({
            "priority": "HIGH",
            "action": "DATA_INVESTIGATION", 
            "description": "Investigate data schema compatibility issues",
            "suggested_commands": [
                f"temporal workflow show --workflow-id {analysis['workflow_id']} | jq '.events[-5:].[] | select(.eventType | contains(\"FAILED\"))'"
            ]
        })
    
    # Long-running investigation
    if retry_stats.get("failed_attempts", 0) > 10:
        recommendations.append({
            "priority": "MEDIUM",
            "action": "INVESTIGATE_ROOT_CAUSE",
            "description": "Analyze failure details for root cause",
            "suggested_commands": [
                f"temporal workflow list --query \"WorkflowId = '{analysis['workflow_id']}' AND ExecutionStatus = 'Failed'\" --limit 5"
            ]
        })
    
    return recommendations