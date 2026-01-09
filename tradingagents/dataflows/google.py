from typing import Annotated
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .googlenews_utils import getNewsData


def get_google_news(
    query: Annotated[str, "Query to search with"],
    curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:
    query = query.replace(" ", "+")

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    news_results = getNewsData(query, before, curr_date)

    news_str = ""

    for news in news_results:
        news_str += (
            f"### {news['title']} (source: {news['source']}) \n\n{news['snippet']}\n\n"
        )

    if len(news_results) == 0:
        return ""

    return f"## {query} Google News, from {before} to {curr_date}:\n\n{news_str}"


def get_global_news_google(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "How many days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 5,
) -> str:
    """Fetch global macroeconomic news using Google News."""

    macro_queries = [
        "macroeconomic news",
        "Federal Reserve interest rates",
        "inflation economy",
        "stock market outlook",
        "global economy",
    ]

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    all_news = []

    for query in macro_queries:
        news_data = getNewsData(query.replace(" ", "+"), before, curr_date)
        all_news.extend(news_data)
        if len(all_news) >= limit:
            break

    if len(all_news) == 0:
        return "No global macroeconomic news found."

    result = f"## Global Macroeconomic News, from {before} to {curr_date}:\n\n"
    for article in all_news[:limit]:
        result += f"### {article['title']} (source: {article['source']})\n\n{article['snippet']}\n\n"

    return result