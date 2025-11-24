"""Command builder for Temporal CLI commands."""

from typing import List, Optional, Any, Dict


class TemporalCommandBuilder:
    """Builder for constructing Temporal CLI commands with proper argument handling."""
    
    def __init__(self, env: Optional[str] = None, timeout_seconds: Optional[float] = None):
        self.env = env
        self.output_format = "json"
        self.time_format = "iso"
        self.timeout_seconds = timeout_seconds
    
    def _build_global_flags(self) -> List[str]:
        """Build global flags that apply to all commands."""
        flags = []
        if self.env:
            flags.extend(["--env", self.env])
        flags.extend(["-o", self.output_format, "--time-format", self.time_format])
        
        # Add command timeout if specified
        if self.timeout_seconds is not None:
            # Convert to Temporal CLI duration format (e.g., "60s")
            timeout_str = f"{int(self.timeout_seconds)}s"
            flags.extend(["--command-timeout", timeout_str])
        
        return flags
    
    def build_workflow_list(self, query: Optional[str] = None, limit: int = 10) -> List[str]:
        """Build workflow list command with optional query filtering."""
        args = ["workflow", "list", "--limit", str(limit)]
        if query and query.strip():
            # Validate query before adding it
            if self._is_valid_query(query):
                args.extend(["--query", query])
            else:
                raise ValueError(f"Invalid query format: {query}")
        return args
    
    def _is_valid_query(self, query: str) -> bool:
        """Basic validation for query strings."""
        if not query or not query.strip():
            return True  # Empty queries are valid
        
        # Check for balanced quotes
        if query.count("'") % 2 != 0:
            return False
        
        # Check for balanced parentheses
        if query.count("(") != query.count(")"):
            return False
        
        return True
    
    def build_workflow_list_with_structured_query(
        self, 
        structured_query: Optional[Dict[str, Any]] = None, 
        limit: int = 10
    ) -> List[str]:
        """Build workflow list command from structured query components."""
        if not structured_query:
            return self.build_workflow_list(None, limit)
        
        # Import here to avoid circular imports
        from .query_builder import create_query_builder
        
        builder = create_query_builder()
        
        # Process field filters
        if "field_filters" in structured_query:
            for field_filter in structured_query["field_filters"]:
                condition = f"{field_filter['field']} {field_filter['operator']} '{field_filter['value']}'"
                builder.custom_condition(condition)
        
        # Process time range filters
        if "time_range_filters" in structured_query:
            for time_filter in structured_query["time_range_filters"]:
                start_time = time_filter["start_time"]
                end_time = time_filter["end_time"]
                condition = f"{time_filter['field']} BETWEEN '{start_time}' AND '{end_time}'"
                builder.custom_condition(condition)
        
        # Process IN filters
        if "in_filters" in structured_query:
            for in_filter in structured_query["in_filters"]:
                values_str = ", ".join([f"'{value}'" for value in in_filter["values"]])
                condition = f"{in_filter['field']} IN ({values_str})"
                builder.custom_condition(condition)
        
        query_string = builder.build()
        return self.build_workflow_list(query_string, limit)
    
    def build_workflow_describe(self, workflow_id: str) -> List[str]:
        """Build workflow describe command."""
        return ["workflow", "describe", "--workflow-id", workflow_id]
    
    def build_workflow_start(
        self,
        workflow_type: str,
        task_queue: str,
        workflow_id: Optional[str] = None,
        input_data: Optional[str] = None
    ) -> List[str]:
        """Build workflow start command."""
        args = ["workflow", "start", "--type", workflow_type, "--task-queue", task_queue]
        if workflow_id:
            args.extend(["--workflow-id", workflow_id])
        if input_data:
            args.extend(["--input", input_data])
        return args
    
    def build_workflow_signal(
        self,
        workflow_id: str,
        signal_name: str,
        input_data: Optional[str] = None
    ) -> List[str]:
        """Build workflow signal command."""
        args = ["workflow", "signal", "--workflow-id", workflow_id, "--name", signal_name]
        if input_data:
            args.extend(["--input", input_data])
        return args
    
    def build_workflow_query(
        self,
        workflow_id: str,
        query_type: str,
        input_data: Optional[str] = None
    ) -> List[str]:
        """Build workflow query command."""
        args = ["workflow", "query", "--workflow-id", workflow_id, "--type", query_type]
        if input_data:
            args.extend(["--input", input_data])
        return args
    
    def build_workflow_cancel(self, workflow_id: str) -> List[str]:
        """Build workflow cancel command."""
        return ["workflow", "cancel", "--workflow-id", workflow_id]
    
    def build_workflow_terminate(
        self,
        workflow_id: str,
        reason: Optional[str] = None
    ) -> List[str]:
        """Build workflow terminate command."""
        args = ["workflow", "terminate", "--workflow-id", workflow_id]
        if reason:
            args.extend(["--reason", reason])
        return args
    
    def build_workflow_history(
        self,
        workflow_id: str,
        run_id: Optional[str] = None
    ) -> List[str]:
        """Build workflow history command."""
        args = ["workflow", "show", "--workflow-id", workflow_id]
        if run_id:
            args.extend(["--run-id", run_id])
        return args
    
    def build_workflow_stack(
        self,
        workflow_id: str,
        run_id: Optional[str] = None
    ) -> List[str]:
        """Build workflow stack command."""
        args = ["workflow", "stack", "--workflow-id", workflow_id]
        if run_id:
            args.extend(["--run-id", run_id])
        return args
    
    def build_full_command(self, workflow_args: List[str]) -> List[str]:
        """Build complete command with global flags."""
        return ["temporal"] + self._build_global_flags() + workflow_args