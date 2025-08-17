from typing import List, Optional

from .core import init_env_from_args, mcp
# Importing registers tools via decorators
from . import workflow  # noqa: F401
from . import guides  # noqa: F401


def main(argv: Optional[List[str]] = None) -> None:
    init_env_from_args(argv)
    mcp.run()


if __name__ == "__main__":
    main()
