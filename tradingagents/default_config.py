"""Default configuration for TradingAgents.

This module provides backward-compatible access to configuration.
New code should use TradingAgentsConfig from tradingagents.config.
"""

import warnings
from typing import Dict, Any

from .config import TradingAgentsConfig


def _create_default_config() -> TradingAgentsConfig:
    """Create the default configuration."""
    return TradingAgentsConfig()


# New-style configuration (recommended)
DEFAULT_TRADING_CONFIG = _create_default_config()

# Legacy dictionary format (deprecated)
# This is kept for backward compatibility with existing code
DEFAULT_CONFIG: Dict[str, Any] = DEFAULT_TRADING_CONFIG.to_legacy_dict()


def get_config() -> TradingAgentsConfig:
    """Get the default configuration.

    Returns:
        TradingAgentsConfig instance
    """
    return TradingAgentsConfig()


def get_legacy_config() -> Dict[str, Any]:
    """Get the default configuration in legacy dictionary format.

    .. deprecated::
        Use get_config() instead.

    Returns:
        Configuration dictionary
    """
    warnings.warn(
        "get_legacy_config() is deprecated. Use get_config() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return TradingAgentsConfig().to_legacy_dict()
