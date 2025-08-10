"""Dev shim: execute the src package without installing.

This keeps `python -m temporal_cli_mcp` working in a checkout by injecting ./src
into sys.path and running the package module `temporal_cli_mcp.__main__` so that
relative imports function correctly.
"""

from typing import List, Optional
import os
import sys
import runpy
import shutil


def main(argv: Optional[List[str]] = None) -> None:
    src_dir = os.path.join(os.path.dirname(__file__), "src")
    if os.path.isdir(src_dir) and src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    # Try to keep stdio clean for MCP by disabling banners/log spam if supported
    os.environ.setdefault("FASTMCP_NO_BANNER", "1")
    os.environ.setdefault("FASTMCP_QUIET", "1")
    # If fastmcp isn't available, try to re-exec under `uv run` to resolve deps.
    if not os.environ.get("TEMPORAL_CLI_MCP_BOOTSTRAPPED"):
        try:
            import fastmcp  # noqa: F401
        except Exception:
            uv = shutil.which("uv")
            if uv:
                os.environ["TEMPORAL_CLI_MCP_BOOTSTRAPPED"] = "1"
                args: List[str] = [
                    uv,
                    "run",
                    "python",
                    "-m",
                    "temporal_cli_mcp",
                ]
                # Preserve any original argv passed after -m temporal_cli_mcp
                if argv is None:
                    # When invoked as -m, sys.argv[0] is the module; pass the rest
                    extra = sys.argv[1:]
                else:
                    extra = argv
                args.extend(extra)
                os.execvp(args[0], args)
            # If uv is not available, fall through and let import fail with a clear error
    # Run the package __main__ as a module to preserve package context for relative imports
    runpy.run_module("temporal_cli_mcp.__main__", run_name="__main__")


if __name__ == "__main__":
    main()