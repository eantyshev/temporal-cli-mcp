from typing import Any, Dict, Optional

from ..core import mcp, run_temporal_command


@mcp.tool()
async def list_workflows(
    query: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """List workflows with input validation and improved error handling."""
    from ..models import WorkflowListRequest
    from ..base import AsyncCommandExecutor, WorkflowCommandHandler
    from ..command_builder import TemporalCommandBuilder
    from ..config import config
    from ..exceptions import ValidationError
    
    try:
        # Validate input
        request = WorkflowListRequest(query=query, limit=limit)
        
        # Pre-validate query syntax if provided
        if request.query:
            from ..query_builder import TemporalQueryBuilder
            is_valid, validation_errors = TemporalQueryBuilder.validate_query(request.query)
            
            if not is_valid:
                error_msg = "Invalid query syntax:\n" + "\n".join(f"• {error}" for error in validation_errors)
                validation_help = TemporalQueryBuilder.get_validation_help(request.query)
                
                if validation_help["suggestions"]:
                    error_msg += "\n\nSuggestions:\n" + "\n".join(f"• {suggestion}" for suggestion in validation_help["suggestions"])
                
                raise ValidationError(error_msg)
        
        # Create executor and builder
        executor = AsyncCommandExecutor()
        builder = TemporalCommandBuilder(env=config.env)
        
        # Build and execute command
        workflow_args = builder.build_workflow_list(request.query, request.limit)
        cmd = builder.build_full_command(workflow_args)
        result = await executor.execute(cmd)
        
        if not result["success"]:
            error_msg = result['stderr']
            
            # Transform common Temporal CLI errors into user-friendly messages
            if "operator 'like' not allowed" in error_msg.lower():
                raise ValidationError(
                    "The 'LIKE' operator is not supported by Temporal. "
                    "Use 'STARTS_WITH' for prefix matching instead.\n"
                    "Example: WorkflowType STARTS_WITH 'onboard'"
                )
            elif "operator" in error_msg.lower() and "not allowed" in error_msg.lower():
                # Extract operator name if possible
                import re
                match = re.search(r"operator '(\w+)' not allowed", error_msg.lower())
                if match:
                    op = match.group(1).upper()
                    from ..query_builder import UNSUPPORTED_OPERATORS
                    if op in UNSUPPORTED_OPERATORS:
                        suggested = UNSUPPORTED_OPERATORS[op]
                        raise ValidationError(
                            f"The '{op}' operator is not supported by Temporal. "
                            f"Use '{suggested}' instead."
                        )
                
                raise ValidationError(f"Unsupported operator in query. {error_msg}")
            else:
                raise Exception(f"Failed to list workflows: {error_msg}")
        
        return result
        
    except Exception as e:
        if "ValidationError" in str(type(e)):
            raise ValidationError(f"Invalid input: {e}")
        raise


@mcp.tool()
async def list_workflows_structured(
    query: Optional[str] = None,
    structured_query: Optional[Dict[str, Any]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """List workflows with support for both string and structured queries.
    
    This enhanced version of list_workflows supports:
    1. Traditional string queries (same as list_workflows)
    2. Structured queries built from components
    
    Only one of 'query' or 'structured_query' should be provided.
    If structured_query is provided, it will be converted to a query string.
    """
    from ..models import EnhancedWorkflowListRequest, StructuredQuery
    from ..base import AsyncCommandExecutor
    from ..command_builder import TemporalCommandBuilder
    from ..config import config
    from ..exceptions import ValidationError
    from ..query_builder import create_query_builder
    
    try:
        # Handle structured query conversion
        final_query = query
        
        if structured_query:
            # Validate structured query
            sq = StructuredQuery(**structured_query)
            
            # Build query string from structured query
            builder = create_query_builder()
            
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
            
            final_query = builder.build()
        
        # Validate the complete request
        request = EnhancedWorkflowListRequest(
            query=final_query,
            structured_query=None,  # We've already processed it
            limit=limit
        )
        
        # Create executor and builder
        executor = AsyncCommandExecutor()
        builder = TemporalCommandBuilder(env=config.env)
        
        # Build and execute command
        workflow_args = builder.build_workflow_list(request.query, request.limit)
        cmd = builder.build_full_command(workflow_args)
        result = await executor.execute(cmd)
        
        if not result["success"]:
            error_msg = result['stderr']
            
            # Transform common Temporal CLI errors into user-friendly messages
            if "operator 'like' not allowed" in error_msg.lower():
                raise ValidationError(
                    "The 'LIKE' operator is not supported by Temporal. "
                    "Use 'STARTS_WITH' for prefix matching instead.\n"
                    "Example: WorkflowType STARTS_WITH 'onboard'"
                )
            elif "operator" in error_msg.lower() and "not allowed" in error_msg.lower():
                # Extract operator name if possible
                import re
                match = re.search(r"operator '(\w+)' not allowed", error_msg.lower())
                if match:
                    op = match.group(1).upper()
                    from ..query_builder import UNSUPPORTED_OPERATORS
                    if op in UNSUPPORTED_OPERATORS:
                        suggested = UNSUPPORTED_OPERATORS[op]
                        raise ValidationError(
                            f"The '{op}' operator is not supported by Temporal. "
                            f"Use '{suggested}' instead."
                        )
                
                raise ValidationError(f"Unsupported operator in query. {error_msg}")
            else:
                raise Exception(f"Failed to list workflows: {error_msg}")
        
        # Add query info to result
        result["query_used"] = final_query
        if structured_query:
            result["structured_query_provided"] = True
        
        return result
        
    except Exception as e:
        if "ValidationError" in str(type(e)):
            raise ValidationError(f"Invalid input: {e}")
        raise
