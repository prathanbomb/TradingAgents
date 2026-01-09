"""Local/cached data vendor implementation."""

from .base import BaseVendor

# Import existing local functions
from ..local import (
    get_YFin_data,
    get_finnhub_news,
    get_finnhub_company_insider_sentiment,
    get_finnhub_company_insider_transactions,
    get_simfin_balance_sheet,
    get_simfin_cashflow,
    get_simfin_income_statements,
    get_reddit_global_news,
    get_reddit_company_news,
)

# Also use local indicators from y_finance
from ..y_finance import get_stock_stats_indicators_window


class LocalVendor(BaseVendor):
    """Data vendor using locally cached data files."""

    vendor_name = "local"

    def get_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> str:
        return get_YFin_data(symbol, start_date, end_date)

    def get_indicators(
        self,
        symbol: str,
        indicator: str,
        curr_date: str,
        look_back_days: int = 30,
    ) -> str:
        # Use yfinance indicators locally - they work offline
        return get_stock_stats_indicators_window(symbol, indicator, curr_date, look_back_days)

    def get_balance_sheet(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        return get_simfin_balance_sheet(symbol, freq, curr_date)

    def get_cashflow(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        return get_simfin_cashflow(symbol, freq, curr_date)

    def get_income_statement(
        self,
        symbol: str,
        freq: str,
        curr_date: str,
    ) -> str:
        return get_simfin_income_statements(symbol, freq, curr_date)

    def get_news(
        self,
        symbol: str,
        curr_date: str,
        look_back_days: int = 7,
    ) -> str:
        # Combine multiple local news sources
        results = []
        try:
            finnhub_news = get_finnhub_news(symbol, curr_date, look_back_days)
            if finnhub_news:
                results.append(finnhub_news)
        except Exception:
            pass

        try:
            reddit_news = get_reddit_company_news(symbol, curr_date, look_back_days)
            if reddit_news:
                results.append(reddit_news)
        except Exception:
            pass

        return "\n".join(results) if results else "No local news data available"

    def get_global_news(
        self,
        curr_date: str,
        look_back_days: int = 7,
        limit: int = 5,
    ) -> str:
        # Reddit global news doesn't support limit, ignore it
        return get_reddit_global_news(curr_date, look_back_days)

    def get_insider_sentiment(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        return get_finnhub_company_insider_sentiment(symbol, curr_date)

    def get_insider_transactions(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        return get_finnhub_company_insider_transactions(symbol, curr_date)

    def supports(self, method: str) -> bool:
        """Check if this vendor supports the given method."""
        supported_methods = {
            "get_stock_data",
            "get_indicators",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement",
            "get_news",
            "get_global_news",
            "get_insider_sentiment",
            "get_insider_transactions",
        }
        return method in supported_methods
