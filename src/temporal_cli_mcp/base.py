"""Abstract base classes for command handling."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .command_builder import TemporalCommandBuilder
from .config import config
from .exceptions import CommandExecutionError, TemporalCLINotFoundError


logger = logging.getLogger(__name__)


class CommandExecutor(ABC):
    """Abstract base class for command execution."""
    
    @abstractmethod
    async def execute(self, cmd: List[str]) -> Dict[str, Any]:
        """Execute a command and return structured result."""
        pass


class AsyncCommandExecutor(CommandExecutor):
    """Async implementation of command executor."""
    
    def __init__(self, timeout: float = None):
        self.timeout = timeout or config.timeout
    
    async def execute(self, cmd: List[str]) -> Dict[str, Any]:
        """Execute command asynchronously."""
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), 
                timeout=self.timeout
            )
            
            stdout_str = stdout.decode('utf-8') if stdout else ""
            stderr_str = stderr.decode('utf-8') if stderr else ""
            
            if proc.returncode == 0:
                try:
                    parsed_data = json.loads(stdout_str) if stdout_str else None
                    # Return parsed JSON data directly, avoiding redundant stdout field
                    result = {
                        "success": True,
                        "returncode": 0,
                        "stderr": stderr_str,
                        "cmd": cmd,
                    }
                    if parsed_data:
                        result.update(parsed_data)
                except json.JSONDecodeError:
                    result = {
                        "success": True,
                        "returncode": 0,
                        "stderr": stderr_str,
                        "cmd": cmd,
                        "json_error": "Failed to parse JSON output from temporal CLI",
                        "raw_output": stdout_str
                    }
            else:
                result = {
                    "success": False,
                    "returncode": proc.returncode,
                    "stderr": stderr_str,
                    "cmd": cmd,
                }
            else:
                logger.error(f"Command failed with return code {proc.returncode}: {stderr_str}")
                
            return result
            
        except FileNotFoundError:
            raise TemporalCLINotFoundError("temporal CLI not found. Please install Temporal CLI.")
        except asyncio.TimeoutError:
            raise CommandExecutionError(
                f"Command timed out after {self.timeout}s",
                cmd, -1, "Timeout"
            )


class CommandHandler(ABC):
    """Abstract base class for command handlers."""
    
    def __init__(self, executor: CommandExecutor, builder: TemporalCommandBuilder):
        self.executor = executor
        self.builder = builder
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the command with given parameters."""
        pass


class WorkflowCommandHandler(CommandHandler):
    """Base class for workflow command handlers."""
    
    async def _execute_workflow_command(self, workflow_args: List[str]) -> Dict[str, Any]:
        """Execute a workflow command with proper error handling."""
        try:
            cmd = self.builder.build_full_command(workflow_args)
            return await self.executor.execute(cmd)
        except Exception as e:
            logger.error(f"Error executing workflow command: {e}")
            raise