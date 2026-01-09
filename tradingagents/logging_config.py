"""Logging configuration for TradingAgents library."""

import logging
import os
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def setup_logging(level: Optional[str] = None) -> None:
    """Setup logging configuration for the library.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
               Defaults to LOG_LEVEL env var or INFO.
    """
    level = level or os.getenv("LOG_LEVEL", "INFO")

    # Configure root logger for tradingagents
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set tradingagents logger level
    logging.getLogger("tradingagents").setLevel(
        getattr(logging, level.upper(), logging.INFO)
    )
