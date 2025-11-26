"""MCP tool for building Temporal workflow queries."""

from typing import Any, Dict

from ..core import mcp


@mcp.tool()
async def build_workflow_query(
    structured_query: Dict[str, Any] = None,
    raw_conditions: list = None,
    logical_operator: str = "AND"
) -> Dict[str, Any]:
    """Build a Temporal workflow list filter query from structured inputs.
    
    This tool helps construct valid Temporal list filter queries using either:
    1. Structured query components (field_filters, time_range_filters, in_filters)
    2. Raw condition strings combined with logical operators
    
    Returns a dictionary with the built query string and validation info.
    """
    from ..models import QueryBuildRequest, StructuredQuery
    from ..query_builder import TemporalQueryBuilder, create_query_builder
    from ..exceptions import ValidationError
    
    try:
        # Validate input using Pydantic models
        if structured_query:
            structured_query_obj = StructuredQuery(**structured_query)
        else:
            structured_query_obj = None
            
        request = QueryBuildRequest(
            structured_query=structured_query_obj,
            raw_conditions=raw_conditions,
            logical_operator=logical_operator
        )
        
        builder = create_query_builder()
        
        # Handle structured query
        if request.structured_query:
            sq = request.structured_query
            
            # Add field filters
            if sq.field_filters:
                for field_filter in sq.field_filters:
                    builder.custom_condition(
                        f"{field_filter.field} {field_filter.operator} '{field_filter.value}'"
                    )
            
            # Add time range filters
            if sq.time_range_filters:
                for time_filter in sq.time_range_filters:
                    start_time = time_filter.start_time
                    end_time = time_filter.end_time
                    
                    # Convert datetime to string if needed
                    if hasattr(start_time, 'isoformat'):
                        start_time = start_time.isoformat()
                    if hasattr(end_time, 'isoformat'):
                        end_time = end_time.isoformat()
                    
                    builder.custom_condition(
                        f"{time_filter.field} BETWEEN '{start_time}' AND '{end_time}'"
                    )
            
            # Add IN filters
            if sq.in_filters:
                for in_filter in sq.in_filters:
                    values_str = ", ".join([f"'{value}'" for value in in_filter.values])
                    builder.custom_condition(f"{in_filter.field} IN ({values_str})")
        
        # Handle raw conditions
        elif request.raw_conditions:
            for condition in request.raw_conditions:
                builder.custom_condition(condition)
        
        # Build the final query
        query_string = builder.build()
        
        # Validate the built query
        is_valid, validation_errors = TemporalQueryBuilder.validate_query(query_string)
        validation_details = TemporalQueryBuilder.get_validation_help(query_string)
        
        return {
            "success": True,
            "query": query_string,
            "is_valid": is_valid,
            "validation_errors": validation_errors,
            "validation_details": validation_details,
            "supported_fields": TemporalQueryBuilder.get_supported_fields(),
            "supported_operators": TemporalQueryBuilder.get_supported_operators(),
            "execution_statuses": TemporalQueryBuilder.get_execution_statuses()
        }
        
    except Exception as e:
        if "ValidationError" in str(type(e)):
            raise ValidationError(f"Invalid query input: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": "",
            "is_valid": False
        }


@mcp.tool()
async def get_query_examples() -> Dict[str, Any]:
    """Get example Temporal workflow list filter queries for common use cases.
    
    Returns a collection of example queries demonstrating different filter types
    and combinations that can be used with the list_workflows command.
    """
    examples = {
        "basic_filters": {
            "workflow_type": "WorkflowType = 'MyWorkflow'",
            "execution_status": "ExecutionStatus = 'Running'",
            "workflow_id": "WorkflowId = 'workflow-123'"
        },
        "pattern_matching": {
            "workflow_name_prefix": "WorkflowType STARTS_WITH 'Patient'",
            "onboarding_workflows": "WorkflowType STARTS_WITH 'onboard'",
            "service_workflows": "WorkflowType STARTS_WITH 'service-'"
        },
        "comparison_filters": {
            "recent_workflows": "StartTime > '2024-01-01T00:00:00Z'",
            "completed_before": "CloseTime < '2024-12-31T23:59:59Z'",
            "long_running": "ExecutionTime > '2024-01-01T00:00:00Z'"
        },
        "advanced_filters": {
            "workflow_id_list": "WorkflowId IN ('wf-1', 'wf-2', 'wf-3')",
            "multiple_types": "WorkflowType IN ('OnboardingFlow', 'UserRegistration', 'OrderProcessing')",
            "time_range": "StartTime BETWEEN '2024-01-01T00:00:00Z' AND '2024-01-31T23:59:59Z'"
        },
        "combined_filters": {
            "running_recent": "ExecutionStatus = 'Running' AND StartTime > '2024-01-01T00:00:00Z'",
            "failed_or_canceled": "ExecutionStatus = 'Failed' OR ExecutionStatus = 'Canceled'",
            "failed_onboarding": "WorkflowType STARTS_WITH 'patient' AND ExecutionStatus = 'Failed'",
            "complex": "(WorkflowType STARTS_WITH 'MyApp' AND ExecutionStatus = 'Running') OR (WorkflowType = 'CriticalWorkflow' AND ExecutionStatus != 'Failed')"
        }
    }
    
    common_mistakes = {
        "avoid_like_operator": {
            "wrong": "WorkflowType LIKE '%onboard%'",
            "correct": "WorkflowType STARTS_WITH 'onboard'",
            "explanation": "LIKE operator is not supported. Use STARTS_WITH for prefix matching."
        },
        "avoid_wildcards": {
            "wrong": "WorkflowType = '*onboard*'",
            "correct": "WorkflowType STARTS_WITH 'onboard'",
            "explanation": "Wildcards are not supported. Use STARTS_WITH for prefix matching."
        },
        "multiple_values": {
            "wrong": "WorkflowType = 'Type1' OR WorkflowType = 'Type2' OR WorkflowType = 'Type3'",
            "correct": "WorkflowType IN ('Type1', 'Type2', 'Type3')",
            "explanation": "Use IN operator for multiple values instead of chaining OR conditions."
        },
        "case_sensitivity": {
            "wrong": "workflowtype = 'MyWorkflow'",
            "correct": "WorkflowType = 'MyWorkflow'",
            "explanation": "Field names are case-sensitive. Use exact field names."
        }
    }
    
    return {
        "success": True,
        "examples": examples,
        "common_mistakes": common_mistakes,
        "usage_notes": [
            "String values must be enclosed in single quotes",
            "Time values should be in ISO format (e.g., '2024-01-01T00:00:00Z')",
            "Use parentheses to group complex logical conditions",
            "Field names are case-sensitive",
            "STARTS_WITH is useful for prefix matching on WorkflowType",
            "Use IN operator for multiple values instead of chaining OR conditions",
            "LIKE operator and wildcards (%, *) are not supported"
        ],
        "supported_fields": [
            "WorkflowId", "WorkflowType", "ExecutionStatus", 
            "StartTime", "CloseTime", "ExecutionTime"
        ],
        "supported_operators": [
            "=", "!=", ">", ">=", "<", "<=", "IN", "BETWEEN", "STARTS_WITH", "AND", "OR"
        ],
        "supported_statuses": [
            "Running", "Completed", "Failed", "Canceled", 
            "Terminated", "ContinuedAsNew", "TimedOut"
        ]
    }


@mcp.tool()
async def validate_workflow_query(query: str) -> Dict[str, Any]:
    """Validate a Temporal workflow list filter query string.
    
    Checks the syntax and structure of a query string to ensure it's valid
    for use with Temporal workflow list commands.
    
    Args:
        query: The query string to validate
        
    Returns:
        Dictionary with validation results and suggestions
    """
    from ..models import QueryValidationRequest
    from ..query_builder import TemporalQueryBuilder
    from ..exceptions import ValidationError
    
    try:
        # Validate input
        request = QueryValidationRequest(query=query)
        
        # Perform validation
        is_valid = TemporalQueryBuilder.validate_query(request.query)
        
        # Additional checks
        validation_issues = []
        suggestions = []
        
        if not request.query.strip():
            return {
                "success": True,
                "is_valid": True,
                "query": request.query,
                "message": "Empty query is valid (returns all workflows)",
                "issues": [],
                "suggestions": []
            }
        
        # Check for common issues
        if "'" not in request.query and any(op in request.query for op in ["=", "!=", "STARTS_WITH"]):
            validation_issues.append("String values should be enclosed in single quotes")
            suggestions.append("Example: WorkflowType = 'MyWorkflow' instead of WorkflowType = MyWorkflow")
        
        if request.query.count("'") % 2 != 0:
            validation_issues.append("Unbalanced single quotes")
            suggestions.append("Ensure all string values are properly quoted")
        
        if request.query.count("(") != request.query.count(")"):
            validation_issues.append("Unbalanced parentheses")
            suggestions.append("Check that all opening parentheses have matching closing ones")
        
        # Check for potentially unrecognized fields (note: custom search attributes are supported)
        supported_fields = TemporalQueryBuilder.get_supported_fields()
        query_upper = request.query.upper()
        unrecognized_fields = []
        
        # Simple field detection (could be more sophisticated)
        words = request.query.split()
        for word in words:
            # Clean up field name (remove backticks, quotes, etc.)
            clean_word = word.strip('`').strip('"').strip("'")
            if clean_word and clean_word[0].isupper() and clean_word not in supported_fields:
                # Might be a field name
                if any(op in request.query for op in ["=", "!=", ">", "<", "STARTS_WITH"]):
                    unrecognized_fields.append(clean_word)
        
        if unrecognized_fields:
            # This is just informational, not an error - could be custom search attributes
            suggestions.append(f"Note: Fields {unrecognized_fields} are not built-in. If these are custom search attributes, ensure they're defined in your Temporal namespace.")
            suggestions.append(f"Built-in fields: {supported_fields}")
        
        # Check for logical operators
        if " and " in request.query.lower():
            validation_issues.append("Logical operators should be uppercase")
            suggestions.append("Use 'AND' instead of 'and'")
        
        if " or " in request.query.lower():
            validation_issues.append("Logical operators should be uppercase")
            suggestions.append("Use 'OR' instead of 'or'")
        
        return {
            "success": True,
            "is_valid": is_valid and len(validation_issues) == 0,
            "query": request.query,
            "issues": validation_issues,
            "suggestions": suggestions,
            "supported_fields": supported_fields,
            "supported_operators": TemporalQueryBuilder.get_supported_operators(),
            "execution_statuses": TemporalQueryBuilder.get_execution_statuses()
        }
        
    except Exception as e:
        if "ValidationError" in str(type(e)):
            raise ValidationError(f"Invalid input: {e}")
        return {
            "success": False,
            "is_valid": False,
            "query": query,
            "error": str(e),
            "issues": ["Failed to validate query"],
            "suggestions": ["Check query syntax and try again"]
        }