"""Google data vendor implementation using Gemini API with Google Search grounding."""

from .base import BaseVendor

from ..gemini import (
    get_google_news_gemini,
    get_global_news_gemini,
)


class GoogleVendor(BaseVendor):
    """Data vendor using Gemini API with Google Search grounding.

    Requires GOOGLE_API_KEY environment variable to be set.
    Get your API key from: https://aistudio.google.com/
    """

    vendor_name = "google"

    def get_news(
        self,
        symbol: str,
        curr_date: str,
        look_back_days: int = 7,
    ) -> str:
        return get_google_news_gemini(symbol, curr_date, look_back_days)

    def get_global_news(
        self,
        curr_date: str,
        look_back_days: int = 7,
        limit: int = 5,
    ) -> str:
        return get_global_news_gemini(curr_date, look_back_days, limit)

    def supports(self, method: str) -> bool:
        """Check if this vendor supports the given method."""
        supported_methods = {
            "get_news",
            "get_global_news",
        }
        return method in supported_methods
