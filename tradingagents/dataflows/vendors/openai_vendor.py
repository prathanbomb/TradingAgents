"""OpenAI-based data vendor implementation."""

from .base import BaseVendor

# Import existing openai functions
from ..openai import (
    get_stock_news_openai,
    get_global_news_openai,
    get_fundamentals_openai,
)


class OpenAIVendor(BaseVendor):
    """Data vendor using OpenAI for data retrieval/generation."""

    vendor_name = "openai"

    def get_fundamentals(
        self,
        symbol: str,
        curr_date: str,
    ) -> str:
        return get_fundamentals_openai(symbol, curr_date)

    def get_news(
        self,
        symbol: str,
        curr_date: str,
        look_back_days: int = 7,
    ) -> str:
        return get_stock_news_openai(symbol, curr_date, look_back_days)

    def get_global_news(
        self,
        curr_date: str,
        look_back_days: int = 7,
        limit: int = 5,
    ) -> str:
        return get_global_news_openai(curr_date, look_back_days, limit)

    def supports(self, method: str) -> bool:
        """Check if this vendor supports the given method."""
        supported_methods = {
            "get_fundamentals",
            "get_news",
            "get_global_news",
        }
        return method in supported_methods
