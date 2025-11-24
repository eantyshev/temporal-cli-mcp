"""Configuration management for Temporal CLI MCP server."""

import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class TemporalConfig:
    """Configuration for Temporal CLI operations."""
    env: Optional[str] = None
    output_format: str = "json"
    time_format: str = "iso"
    log_level: str = "INFO"
    timeout: float = 60.0  # Default 60s - increase for large workflow histories
    
    def setup_logging(self) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


# Global configuration instance
config = TemporalConfig()