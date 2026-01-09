"""Alpha Vantage data vendor implementation."""

from .base import BaseVendor

# Import existing alpha vantage functions
from ..alpha_vantage import (
    get_stock as av_get_stock,
    get_indicator as av_get_indicator,
    get_fundamentals as av_get_fundamentals,
    get_balance_sheet as av_get_balance_sheet,
    get_cashflow as av_get_cashflow,
    get_income_statement as av_get_income_statement,
    get_insider_transactions as av_get_insider_transactions,
    get_news as av_get_news,
)


class AlphaVantageVendor(BaseVendor):
    """Data vendor using Alpha Vantage API."""

    vendor_name = "alpha_vantage"

    def get_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> str:
        return av_get_stock(symbol, start_date, end_date)

    def get_indicators(
        self,
        symbol: str,
        indicator: str,
        curr_date: str,
        look_back_days: int = 30,
    ) -> str:
        return av_get_indicator(symbol, indicator, curr_date, look_back_days)

    def get_fundamentals(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        return av_get_fundamentals(symbol, curr_date)

    def get_balance_sheet(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        return av_get_balance_sheet(symbol, freq, curr_date)

    def get_cashflow(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        return av_get_cashflow(symbol, freq, curr_date)

    def get_income_statement(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        return av_get_income_statement(symbol, freq, curr_date)

    def get_news(
        self,
        symbol: str,
        curr_date: str,
        look_back_days: int = 7,
    ) -> str:
        return av_get_news(symbol, curr_date, look_back_days)

    def get_insider_transactions(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        return av_get_insider_transactions(symbol, curr_date)

    def supports(self, method: str) -> bool:
        """Check if this vendor supports the given method."""
        supported_methods = {
            "get_stock_data",
            "get_indicators",
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement",
            "get_news",
            "get_insider_transactions",
        }
        return method in supported_methods
