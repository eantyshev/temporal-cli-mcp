import argparse
import json
import subprocess
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP


# MCP server instance
mcp = FastMCP("Temporal CLI MCP Server")

# Global prefix for Temporal CLI commands, e.g. ["--env", "prod"].
_TEMPORAL_GLOBAL_PREFIX: List[str] = []


async def run_temporal_command(args: List[str], *, output: str = "json") -> Dict[str, Any]:
    """Execute a temporal CLI command and return the result with optional JSON parsing.

    DEPRECATED: Use AsyncCommandExecutor with TemporalCommandBuilder instead.
    This function is kept for backward compatibility.
    """
    from .base import AsyncCommandExecutor
    from .command_builder import TemporalCommandBuilder
    from .config import config
    
    # Create executor and builder
    executor = AsyncCommandExecutor()
    builder = TemporalCommandBuilder(env=config.env)
    
    # Build command with global flags
    global_flags: List[str] = list(_TEMPORAL_GLOBAL_PREFIX)
    if output == "json":
        global_flags += ["-o", "json", "--time-format", "iso"]
    
    cmd = ["temporal"] + global_flags + args
    return await executor.execute(cmd)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="temporal-cli-mcp",
        add_help=True,
        description=(
            "MCP server that wraps 'temporal workflow' commands. "
            "Pass --env to select a Temporal CLI environment. Output is JSON."
        ),
    )
    parser.add_argument(
        "--env",
        dest="env",
        metavar="VALUE",
        help="If provided, prepends `--env VALUE` to all Temporal CLI invocations.",
    )
    return parser


def init_env_from_args(argv: Optional[List[str]] = None) -> None:
    from .config import config
    
    global _TEMPORAL_GLOBAL_PREFIX
    parser = build_arg_parser()
    args, _unknown = parser.parse_known_args(argv)
    
    if args.env:
        _TEMPORAL_GLOBAL_PREFIX = ["--env", args.env]
        config.env = args.env
    
    # Setup logging
    config.setup_logging()


__all__ = [
    "mcp",
    "run_temporal_command",
    "build_arg_parser",
    "init_env_from_args",
]
