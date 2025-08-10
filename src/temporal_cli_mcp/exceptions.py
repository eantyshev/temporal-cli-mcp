"""Custom exceptions for Temporal CLI MCP server."""


class TemporalCLIError(Exception):
    """Base exception for Temporal CLI operations."""
    pass


class CommandExecutionError(TemporalCLIError):
    """Raised when CLI command execution fails."""
    
    def __init__(self, message: str, cmd: list[str], returncode: int, stderr: str = ""):
        super().__init__(message)
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr


class TemporalCLINotFoundError(TemporalCLIError):
    """Raised when the temporal CLI is not found in PATH."""
    pass


class ValidationError(TemporalCLIError):
    """Raised when input validation fails."""
    pass