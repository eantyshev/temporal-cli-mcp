"""Command builder for Temporal CLI commands."""

from typing import List, Optional, Any, Dict


class TemporalCommandBuilder:
    """Builder for constructing Temporal CLI commands with proper argument handling."""
    
    def __init__(self, env: Optional[str] = None):
        self.env = env
        self.output_format = "json"
        self.time_format = "iso"
    
    def _build_global_flags(self) -> List[str]:
        """Build global flags that apply to all commands."""
        flags = []
        if self.env:
            flags.extend(["--env", self.env])
        flags.extend(["-o", self.output_format, "--time-format", self.time_format])
        return flags
    
    def build_workflow_list(self, query: Optional[str] = None, limit: int = 10) -> List[str]:
        """Build workflow list command."""
        args = ["workflow", "list", "--limit", str(limit)]
        if query:
            args.extend(["--query", query])
        return args
    
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
        follow: bool = False
    ) -> List[str]:
        """Build workflow history command."""
        args = ["workflow", "show", "--workflow-id", workflow_id]
        if follow:
            args.append("--follow")
        return args
    
    def build_full_command(self, workflow_args: List[str]) -> List[str]:
        """Build complete command with global flags."""
        return ["temporal"] + self._build_global_flags() + workflow_args