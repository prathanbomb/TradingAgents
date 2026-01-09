"""Vendor registry for managing and routing to data providers."""

import logging
from typing import Dict, List, Optional, Type

from .base import BaseVendor, DataVendor

logger = logging.getLogger(__name__)


class VendorNotFoundError(Exception):
    """Raised when a requested vendor is not registered."""
    pass


class MethodNotSupportedError(Exception):
    """Raised when a vendor does not support the requested method."""
    pass


class VendorRegistry:
    """Registry for data vendor implementations.

    Provides a centralized place to register and retrieve vendor implementations.
    Supports routing method calls to the appropriate vendor.
    """

    _vendors: Dict[str, BaseVendor] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, vendor: BaseVendor) -> None:
        """Register a vendor implementation.

        Args:
            vendor: The vendor instance to register
        """
        cls._vendors[vendor.vendor_name] = vendor
        logger.debug(f"Registered vendor: {vendor.vendor_name}")

    @classmethod
    def unregister(cls, vendor_name: str) -> None:
        """Unregister a vendor.

        Args:
            vendor_name: Name of the vendor to unregister
        """
        if vendor_name in cls._vendors:
            del cls._vendors[vendor_name]
            logger.debug(f"Unregistered vendor: {vendor_name}")

    @classmethod
    def get_vendor(cls, name: str) -> BaseVendor:
        """Get a vendor by name.

        Args:
            name: The vendor name

        Returns:
            The registered vendor instance

        Raises:
            VendorNotFoundError: If vendor is not registered
        """
        cls._ensure_initialized()
        if name not in cls._vendors:
            available = ", ".join(cls._vendors.keys())
            raise VendorNotFoundError(
                f"Vendor '{name}' not registered. Available vendors: {available}"
            )
        return cls._vendors[name]

    @classmethod
    def list_vendors(cls) -> List[str]:
        """List all registered vendor names.

        Returns:
            List of vendor names
        """
        cls._ensure_initialized()
        return list(cls._vendors.keys())

    @classmethod
    def route(
        cls,
        method: str,
        vendor_name: str,
        *args,
        **kwargs,
    ) -> str:
        """Route a method call to the specified vendor.

        Args:
            method: The method name to call (e.g., 'get_stock_data')
            vendor_name: The vendor to use
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method

        Returns:
            The result from the vendor method

        Raises:
            VendorNotFoundError: If vendor is not registered
            MethodNotSupportedError: If vendor doesn't support the method
        """
        vendor = cls.get_vendor(vendor_name)

        if not hasattr(vendor, method):
            raise MethodNotSupportedError(
                f"Vendor '{vendor_name}' does not have method '{method}'"
            )

        func = getattr(vendor, method)
        try:
            return func(*args, **kwargs)
        except NotImplementedError:
            raise MethodNotSupportedError(
                f"Vendor '{vendor_name}' does not support '{method}'"
            )

    @classmethod
    def get_vendors_for_method(cls, method: str) -> List[str]:
        """Get list of vendors that support a specific method.

        Args:
            method: The method name to check

        Returns:
            List of vendor names that support the method
        """
        cls._ensure_initialized()
        supported = []
        for name, vendor in cls._vendors.items():
            if hasattr(vendor, method):
                # Check if method is actually implemented (not just inherited)
                try:
                    # Try calling with dummy args to see if it raises NotImplementedError
                    # This is a bit hacky but works for our use case
                    if vendor.supports(method):
                        supported.append(name)
                except Exception:
                    # If supports() fails, assume it's supported
                    supported.append(name)
        return supported

    @classmethod
    def clear(cls) -> None:
        """Clear all registered vendors."""
        cls._vendors.clear()
        cls._initialized = False
        logger.debug("Cleared vendor registry")

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure the registry is initialized with default vendors."""
        if not cls._initialized:
            cls._initialize_default_vendors()

    @classmethod
    def _initialize_default_vendors(cls) -> None:
        """Initialize the registry with default vendor implementations."""
        # Import vendor implementations here to avoid circular imports
        from .yfinance_vendor import YFinanceVendor
        from .alpha_vantage_vendor import AlphaVantageVendor
        from .google_vendor import GoogleVendor
        from .local_vendor import LocalVendor
        from .openai_vendor import OpenAIVendor

        # Register default vendors
        cls.register(YFinanceVendor())
        cls.register(AlphaVantageVendor())
        cls.register(GoogleVendor())
        cls.register(LocalVendor())
        cls.register(OpenAIVendor())

        cls._initialized = True
        logger.debug(f"Initialized default vendors: {cls.list_vendors()}")
