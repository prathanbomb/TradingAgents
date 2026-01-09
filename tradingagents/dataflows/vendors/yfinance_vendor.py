"""YFinance data vendor implementation."""

from .base import BaseVendor

# Import existing yfinance functions
from ..y_finance import (
    get_YFin_data_online,
    get_stock_stats_indicators_window,
    get_balance_sheet as yf_get_balance_sheet,
    get_cashflow as yf_get_cashflow,
    get_income_statement as yf_get_income_statement,
    get_insider_transactions as yf_get_insider_transactions,
    get_fundamentals as yf_get_fundamentals,
)


class YFinanceVendor(BaseVendor):
    """Data vendor using Yahoo Finance (yfinance)."""

    vendor_name = "yfinance"

    def get_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> str:
        return get_YFin_data_online(symbol, start_date, end_date)

    def get_indicators(
        self,
        symbol: str,
        indicator: str,
        curr_date: str,
        look_back_days: int = 30,
    ) -> str:
        return get_stock_stats_indicators_window(symbol, indicator, curr_date, look_back_days)

    def get_fundamentals(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        return yf_get_fundamentals(symbol, curr_date)

    def get_balance_sheet(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        return yf_get_balance_sheet(symbol, freq, curr_date)

    def get_cashflow(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        return yf_get_cashflow(symbol, freq, curr_date)

    def get_income_statement(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        return yf_get_income_statement(symbol, freq, curr_date)

    def get_insider_transactions(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        return yf_get_insider_transactions(symbol, curr_date)

    def supports(self, method: str) -> bool:
        """Check if this vendor supports the given method."""
        supported_methods = {
            "get_stock_data",
            "get_indicators",
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement",
            "get_insider_transactions",
        }
        return method in supported_methods
