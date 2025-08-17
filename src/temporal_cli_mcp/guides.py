"""Guides and reference docs exposed via MCP.

Provides a general, callable guide for workflow failure analysis so MCP clients
can fetch decision flows and recommended tools programmatically.
"""

from typing import Any, Dict, List

from .core import mcp


@mcp.tool()
async def workflow_failure_analysis_guide() -> Dict[str, Any]:
    """
    General guide for workflow failure analysis: what to check and which tools to call.

    Returns a structured object with a concise decision flow, concrete MCP tools to use,
    and a checklist of signals to look for in Temporal.

    Intended for SWE/SRE triage and LLM agents.
    """
    decision_flow: List[Dict[str, Any]] = [
        {
            "step": 1,
            "question": "Are we investigating retries or a possible retry storm?",
            "action": "Call get_failed_runs(workflow_id)",
            "tool": "get_failed_runs",
            "why": "Fast, lightweight count of failed attempts (works for running and completed workflows)",
            "next": "If failed_count is high (e.g., > 10), proceed to analyze_workflow_run for deep dive"
        },
        {
            "step": 2,
            "question": "Do we need comprehensive diagnostics (timeline, patterns, recommendations)?",
            "action": "Call analyze_workflow_run(workflow_id)",
            "tool": "analyze_workflow_run",
            "why": "Aggregates retry stats, scans history for patterns, and suggests remediation"
        },
        {
            "step": 3,
            "question": "Do we need raw execution details to confirm the root cause?",
            "action": "Call get_workflow_history(workflow_id) and/or describe_workflow(workflow_id)",
            "tool": ["get_workflow_history", "describe_workflow"],
            "why": "History reveals failure events, signals, child workflows; describe shows current status"
        },
        {
            "step": 4,
            "question": "Is the workflow stuck or blocked right now?",
            "action": "Call trace_workflow(workflow_id)",
            "tool": "trace_workflow",
            "why": "Fetches stack trace/goroutine info to diagnose stalls"
        },
        {
            "step": 5,
            "question": "Need population-level impact or to find similar failures?",
            "action": "Use count_workflows and list_workflows with queries (or build_workflow_query)",
            "tool": ["count_workflows", "list_workflows", "build_workflow_query", "validate_workflow_query", "get_query_examples"],
            "why": "Quantify scope, enumerate affected runs, and construct safe list filters"
        },
        {
            "step": 6,
            "question": "Is an operational action required?",
            "action": "Consider reset_workflow, terminate_workflow, or cancel_workflow",
            "tool": ["reset_workflow", "terminate_workflow", "cancel_workflow"],
            "why": "Break retry loops/timeouts, stop storms, or reset to a good point",
            "note": "Use sparingly and record a reason"
        },
    ]

    what_to_look_for = [
        "Retry storm indicators: rapidly rising failed_count, repeated similar failures",
        "Timeout patterns: consistent durations before failure, repeated activity timeouts",
        "Data issues: schema mismatches, payload decoding errors, consistent input-related failures",
        "External deps: activity failures pointing to downstream services (HTTP/gRPC error codes)",
        "Signals/queries: unexpected signals, missing signals, long-running queries",
        "Child workflows: cascaded failures or fan-out hotspots",
        "Stalls: long gaps in history or active stack traces stuck in I/O waits",
    ]

    recommended_queries = [
        {
            "goal": "All failed runs for a workflow",
            "query": "WorkflowId = '<ID>' AND ExecutionStatus = 'Failed'"
        },
        {
            "goal": "Recent failures by type",
            "tip": "Filter by WorkflowType and closeTime",
            "query": "WorkflowType = 'TypeName' AND ExecutionStatus = 'Failed' AND CloseTime >= '2025-08-01T00:00:00Z'"
        },
        {
            "goal": "Stuck/running for a long time",
            "tip": "Use RunTime or StartTime bounds as appropriate",
            "query": "ExecutionStatus = 'Running' AND RunTime >= 'PT1H'"
        },
    ]

    mapping_to_tools = {
        "retry_counts": "get_failed_runs",
        "deep_diagnostics": "analyze_workflow_run",
        "raw_history": "get_workflow_history",
        "status_snapshot": "describe_workflow",
        "stack_traces": "trace_workflow",
        "population_scope": ["count_workflows", "list_workflows", "build_workflow_query", "validate_workflow_query"],
        "operational_actions": ["reset_workflow", "terminate_workflow", "cancel_workflow"],
    }

    summary = (
        "Start with get_failed_runs for fast retry assessment; escalate to "
        "analyze_workflow_run for comprehensive diagnostics. Use history/describe "
        "to confirm hypotheses; trace_workflow for stalls. Use count/list with the "
        "query builder to assess scope; apply reset/terminate/cancel carefully."
    )

    return {
        "success": True,
        "title": "Workflow Failure Analysis Guide",
        "content_type": "text/markdown",
        "summary": summary,
        "decision_flow": decision_flow,
        "what_to_look_for": what_to_look_for,
        "recommended_queries": recommended_queries,
        "tools": mapping_to_tools,
        "notes": [
            "Analyze on a representative run before applying bulk actions.",
            "Record reasons when resetting/terminating workflows.",
            "Prefer count_workflows before list_workflows to keep responses small.",
        ],
    }
