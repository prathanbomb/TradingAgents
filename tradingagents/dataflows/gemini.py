"""Gemini API with Google Search grounding for news retrieval."""

import logging
from typing import Annotated

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def _format_grounding_response(response) -> str:
    """Format Gemini response with grounding metadata into readable text."""
    result_parts = []

    # Get the main text response
    if response.text:
        result_parts.append(response.text)

    # Add source citations if available
    if hasattr(response, "candidates") and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
            metadata = candidate.grounding_metadata

            # Add sources
            if hasattr(metadata, "grounding_chunks") and metadata.grounding_chunks:
                result_parts.append("\n\n### Sources:")
                for chunk in metadata.grounding_chunks:
                    if hasattr(chunk, "web") and chunk.web:
                        title = getattr(chunk.web, "title", "Unknown")
                        uri = getattr(chunk.web, "uri", "")
                        result_parts.append(f"- [{title}]({uri})")

    return "\n".join(result_parts)


def get_google_news_gemini(
    query: Annotated[str, "Query to search with (e.g., stock ticker or company name)"],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "How many days to look back"],
) -> str:
    """Fetch news using Gemini with Google Search grounding.

    Args:
        query: Search query (stock ticker or company name)
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back for news

    Returns:
        Formatted news report with headlines, summaries, and sources
    """
    try:
        client = genai.Client()  # Uses GOOGLE_API_KEY env var

        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])

        prompt = f"""Find recent news articles about {query} from the past {look_back_days} days.
Today's date is {curr_date}.

For each article, provide:
- Headline
- Source/Publisher
- Brief summary (1-2 sentences)

Focus on financial news, market analysis, and significant company developments.
List the most relevant and recent articles first."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )

        formatted = _format_grounding_response(response)
        if formatted:
            return f"## {query} News (via Google Search), past {look_back_days} days:\n\n{formatted}"
        return f"No recent news found for {query}"

    except Exception as e:
        logger.warning(f"Gemini Google Search failed for {query}: {e}")
        return f"Unable to fetch news for {query}: {str(e)}"


def get_global_news_gemini(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "How many days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 5,
) -> str:
    """Fetch global macroeconomic news using Gemini with Google Search.

    Args:
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back for news
        limit: Maximum number of articles to return

    Returns:
        Formatted global news report with headlines and summaries
    """
    try:
        client = genai.Client()  # Uses GOOGLE_API_KEY env var

        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])

        prompt = f"""Find the top {limit} most important global macroeconomic and financial market news from the past {look_back_days} days.
Today's date is {curr_date}.

Focus on:
- Federal Reserve and central bank decisions
- Inflation and economic indicators
- Major stock market movements
- Global economic outlook
- Significant policy changes

For each article, provide:
- Headline
- Source/Publisher
- Brief summary (1-2 sentences)
- Why it matters for investors

List the most impactful news first."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )

        formatted = _format_grounding_response(response)
        if formatted:
            return f"## Global Macroeconomic News (via Google Search), past {look_back_days} days:\n\n{formatted}"
        return "No global macroeconomic news found."

    except Exception as e:
        logger.warning(f"Gemini Google Search failed for global news: {e}")
        return f"Unable to fetch global news: {str(e)}"
