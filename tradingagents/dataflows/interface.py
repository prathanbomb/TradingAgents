"""Data interface module with vendor routing.

This module provides a unified interface for data retrieval,
routing requests to the appropriate vendor based on configuration.
"""

import logging
import time
from typing import List, Dict, Any, Tuple

from .vendors import VendorRegistry, VendorNotFoundError, MethodNotSupportedError
from .config import get_config
from .alpha_vantage_common import AlphaVantageRateLimitError

logger = logging.getLogger(__name__)

# TTL cache for vendor requests (5 minute TTL, max 100 entries)
_request_cache: Dict[Tuple, Tuple[Any, float]] = {}
_CACHE_TTL = 300  # seconds
_CACHE_MAX_SIZE = 100


def _get_cache_key(method: str, args: tuple, kwargs: dict) -> Tuple:
    """Create a hashable cache key from method call parameters."""
    return (method, args, tuple(sorted(kwargs.items())))


def _cache_get(key: Tuple) -> Tuple[bool, Any]:
    """Get value from cache if exists and not expired."""
    if key in _request_cache:
        value, timestamp = _request_cache[key]
        if time.time() - timestamp < _CACHE_TTL:
            logger.debug(f"Cache hit for {key[0]}")
            return True, value
        else:
            del _request_cache[key]
    return False, None


def _cache_set(key: Tuple, value: Any) -> None:
    """Set value in cache with current timestamp."""
    # Evict oldest entries if cache is full
    if len(_request_cache) >= _CACHE_MAX_SIZE:
        oldest_key = min(_request_cache.keys(), key=lambda k: _request_cache[k][1])
        del _request_cache[oldest_key]
    _request_cache[key] = (value, time.time())

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": ["get_stock_data"],
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": ["get_indicators"],
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement",
        ],
    },
    "news_data": {
        "description": "News (public/insiders, original/processed)",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_sentiment",
            "get_insider_transactions",
        ],
    },
}


def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")


def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.

    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "yfinance")


def get_available_vendors_for_method(method: str) -> List[str]:
    """Get list of vendors that support a specific method.

    Args:
        method: The method name (e.g., 'get_stock_data')

    Returns:
        List of vendor names that support the method
    """
    return VendorRegistry.get_vendors_for_method(method)


def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation with fallback support.

    Args:
        method: The method name to call
        *args: Positional arguments for the method
        **kwargs: Keyword arguments for the method

    Returns:
        Result from the vendor method

    Raises:
        RuntimeError: If all vendor implementations fail
    """
    # Check cache first
    cache_key = _get_cache_key(method, args, kwargs)
    hit, cached_value = _cache_get(cache_key)
    if hit:
        return cached_value

    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)

    # Handle comma-separated vendors
    primary_vendors = [v.strip() for v in vendor_config.split(",")]

    # Get all available vendors for this method for fallback
    all_available_vendors = get_available_vendors_for_method(method)

    # Create fallback vendor list: primary vendors first, then remaining vendors
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    # Log fallback ordering
    primary_str = " -> ".join(primary_vendors)
    fallback_str = " -> ".join(fallback_vendors)
    logger.debug(f"{method} - Primary: [{primary_str}] | Full fallback order: [{fallback_str}]")

    # Track results and execution state
    results = []
    vendor_attempt_count = 0
    successful_vendor = None

    for vendor_name in fallback_vendors:
        # Check if vendor supports this method
        if vendor_name not in all_available_vendors:
            if vendor_name in primary_vendors:
                logger.info(
                    f"Vendor '{vendor_name}' not supported for method '{method}', "
                    "falling back to next vendor"
                )
            continue

        vendor_attempt_count += 1
        is_primary_vendor = vendor_name in primary_vendors

        # Log current attempt
        vendor_type = "PRIMARY" if is_primary_vendor else "FALLBACK"
        logger.debug(
            f"Attempting {vendor_type} vendor '{vendor_name}' for {method} "
            f"(attempt #{vendor_attempt_count})"
        )

        try:
            result = VendorRegistry.route(method, vendor_name, *args, **kwargs)
            results.append(result)
            successful_vendor = vendor_name
            logger.debug(f"Vendor '{vendor_name}' succeeded")

            # Stop after first successful vendor for single-vendor configs
            if len(primary_vendors) == 1:
                logger.debug(f"Stopping after successful vendor '{vendor_name}'")
                break

        except AlphaVantageRateLimitError as e:
            logger.warning(
                f"Alpha Vantage rate limit exceeded, falling back to next vendor"
            )
            logger.debug(f"Rate limit details: {e}")
            continue

        except MethodNotSupportedError as e:
            logger.debug(f"Vendor '{vendor_name}' does not support '{method}': {e}")
            continue

        except VendorNotFoundError as e:
            logger.warning(f"Vendor '{vendor_name}' not found: {e}")
            continue

        except Exception as e:
            logger.warning(f"Vendor '{vendor_name}' failed for {method}: {e}")
            continue

    # Final result summary
    if not results:
        logger.error(f"All {vendor_attempt_count} vendor attempts failed for method '{method}'")
        raise RuntimeError(f"All vendor implementations failed for method '{method}'")

    logger.debug(
        f"Method '{method}' completed with {len(results)} result(s) "
        f"from {vendor_attempt_count} vendor attempt(s)"
    )

    # Return single result if only one, otherwise concatenate as string
    if len(results) == 1:
        result = results[0]
    else:
        result = "\n".join(str(r) for r in results)

    # Cache the result
    _cache_set(cache_key, result)
    return result
