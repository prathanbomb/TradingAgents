"""Base vendor protocol and interfaces for data providers."""

from abc import ABC, abstractmethod
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class DataVendor(Protocol):
    """Protocol defining the interface for data vendor implementations.

    All vendor implementations must provide a vendor_name and implement
    the methods they support. Methods not supported should raise NotImplementedError.
    """

    vendor_name: str

    def get_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> str:
        """Get OHLCV stock price data."""
        ...

    def get_indicators(
        self,
        symbol: str,
        indicator: str,
        curr_date: str,
        look_back_days: int = 30,
    ) -> str:
        """Get technical indicators."""
        ...

    def get_fundamentals(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        """Get company fundamentals."""
        ...

    def get_balance_sheet(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        """Get balance sheet data."""
        ...

    def get_cashflow(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        """Get cash flow statement."""
        ...

    def get_income_statement(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        """Get income statement."""
        ...

    def get_news(
        self,
        symbol: str,
        curr_date: str,
        look_back_days: int = 7,
    ) -> str:
        """Get company news."""
        ...

    def get_global_news(
        self,
        curr_date: str,
        look_back_days: int = 7,
        limit: int = 5,
    ) -> str:
        """Get global market news."""
        ...

    def get_insider_sentiment(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        """Get insider sentiment data."""
        ...

    def get_insider_transactions(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        """Get insider transaction data."""
        ...


class BaseVendor(ABC):
    """Abstract base class for vendor implementations.

    Provides default NotImplementedError for all methods.
    Subclasses should override the methods they support.
    """

    vendor_name: str = "base"

    def get_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_stock_data")

    def get_indicators(
        self,
        symbol: str,
        indicator: str,
        curr_date: str,
        look_back_days: int = 30,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_indicators")

    def get_fundamentals(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_fundamentals")

    def get_balance_sheet(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_balance_sheet")

    def get_cashflow(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_cashflow")

    def get_income_statement(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_income_statement")

    def get_news(
        self,
        symbol: str,
        curr_date: str,
        look_back_days: int = 7,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_news")

    def get_global_news(
        self,
        curr_date: str,
        look_back_days: int = 7,
        limit: int = 5,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_global_news")

    def get_insider_sentiment(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_insider_sentiment")

    def get_insider_transactions(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        raise NotImplementedError(f"{self.vendor_name} does not support get_insider_transactions")

    def supports(self, method: str) -> bool:
        """Check if this vendor supports the given method."""
        try:
            func = getattr(self, method)
            # Try to call to check if it raises NotImplementedError
            # This is a heuristic - we check if the method is overridden
            base_func = getattr(BaseVendor, method, None)
            return func.__func__ is not base_func
        except AttributeError:
            return False
