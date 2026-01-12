"""
TL;DR (Too Long; Didn't Read) summary extraction for trading reports.

This module provides template-based extraction functions to generate concise
summaries at the top of each trading report.
"""

import re
from typing import Dict, Any


def extract_tldr(content: str, report_type: str, metadata: Dict[str, Any]) -> str:
    """
    Extract TL;DR summary from report content.

    Args:
        content: The full report content
        report_type: Type of report (e.g., 'market_report', 'final_trade_decision')
        metadata: Additional metadata (ticker, date, price, etc.)

    Returns:
        TL;DR summary in Markdown format
    """
    extractor_map = {
        "market_report": extract_market_tldr,
        "fundamentals_report": extract_fundamentals_tldr,
        "news_report": extract_news_tldr,
        "sentiment_report": extract_sentiment_tldr,
        "investment_plan": extract_investment_plan_tldr,
        "trader_investment_plan": extract_trader_plan_tldr,
        "final_trade_decision": extract_final_decision_tldr,
    }

    extractor = extractor_map.get(report_type, extract_generic_tldr)
    return extractor(content, metadata)


def extract_market_tldr(content: str, metadata: Dict[str, Any]) -> str:
    """Extract TL;DR from market technical analysis report."""
    ticker = metadata.get("ticker", "N/A")
    date = metadata.get("date", "N/A")

    # Extract current price - try multiple patterns
    price_match = re.search(r"Current Price:?\s*\$?([\d,]+\.?\d*)", content)
    if not price_match:
        price_match = re.search(r"\*\*Current Price:?\*\*\s*\$?([\d,]+\.?\d*)", content)
    price = price_match.group(1) if price_match else "N/A"

    # Extract recommendation from assessment section
    recommendation = "HOLD"  # default
    assessment_match = re.search(
        r"Technical Outlook:?\s*\*\*(.*?)\*\*", content, re.IGNORECASE
    )
    if assessment_match:
        outlook = assessment_match.group(1).upper()
        if "BULLISH" in outlook:
            recommendation = "BUY"
        elif "BEARISH" in outlook:
            recommendation = "SELL"

    # Extract RSI from table or text - be more specific
    rsi_match = re.search(r"\|\s*\*?\*?RSI\*?\*?\s*\|\s*([\d.]+)", content, re.IGNORECASE)
    if not rsi_match:
        rsi_match = re.search(r"RSI[^|\d]*[:\|]\s*([\d.]+)", content, re.IGNORECASE)
    rsi = rsi_match.group(1) if rsi_match else "N/A"

    # Extract 50-day SMA from table
    sma50_match = re.search(r"\|\s*\*?\*?50[^|\n]*SMA\*?\*?\s*\|\s*\$?([\d.]+)", content, re.IGNORECASE)
    if not sma50_match:
        sma50_match = re.search(r"50[^|\n]*SMA[^|\n]*[:\|]\s*\$?([\d.]+)", content, re.IGNORECASE)
    sma50 = sma50_match.group(1) if sma50_match else "N/A"

    # Extract 200-day SMA from table
    sma200_match = re.search(r"\|\s*\*?\*?200[^|\n]*SMA\*?\*?\s*\|\s*\$?([\d.]+)", content, re.IGNORECASE)
    if not sma200_match:
        sma200_match = re.search(r"200[^|\n]*SMA[^|\n]*[:\|]\s*\$?([\d.]+)", content, re.IGNORECASE)
    sma200 = sma200_match.group(1) if sma200_match else "N/A"

    # Extract MACD from table
    macd_match = re.search(r"\|\s*\*?\*?MACD\*?\*?\s*\|\s*([-\d.]+)", content, re.IGNORECASE)
    if not macd_match:
        macd_match = re.search(r"MACD[^|\d-]*[:\|]\s*([-\d.]+)", content, re.IGNORECASE)
    macd = macd_match.group(1) if macd_match else "N/A"

    # Extract one-line summary from conclusion if available
    summary_lines = []
    conclusion_match = re.search(
        r"Conclusion:?\s*(.*?)(?:\n\n|\Z)", content, re.IGNORECASE | re.DOTALL
    )
    if conclusion_match:
        conclusion_text = conclusion_match.group(1).strip()
        # Get first sentence or first 150 chars
        summary_lines.append(conclusion_text.split(".")[0][:150])

    # Build TL;DR
    key_points = []
    if rsi != "N/A":
        try:
            rsi_val = float(rsi)
            rsi_status = "oversold" if rsi_val < 30 else "overbought" if rsi_val > 70 else "neutral"
            key_points.append(f"**RSI:** {rsi} ({rsi_status})")
        except ValueError:
            key_points.append(f"**RSI:** {rsi}")
    if sma50 != "N/A":
        key_points.append(f"**50-day SMA:** ${sma50}")
    if sma200 != "N/A":
        key_points.append(f"**200-day SMA:** ${sma200}")
    if macd != "N/A":
        macd_status = "bearish" if "-" in macd else "bullish"
        key_points.append(f"**MACD:** {macd} ({macd_status})")

    one_liner = " ".join(summary_lines)[:200] if summary_lines else f"Technical analysis for {ticker} with key indicators as shown above."

    return f"""## TL;DR Summary

**Ticker:** {ticker} | **Date:** {date} | **Current Price:** ${price}

### Key Points
- **Recommendation:** {recommendation}
{chr(10).join(f'- {point}' for point in key_points)}

### One-Line Summary
{one_liner}

---


"""


def extract_fundamentals_tldr(content: str, metadata: Dict[str, Any]) -> str:
    """Extract TL;DR from fundamentals analysis report."""
    ticker = metadata.get("ticker", "N/A")
    date = metadata.get("date", "N/A")

    # Extract revenue
    revenue_match = re.search(
        r"Revenue[^:]*:?\s*\$?([\d.]+\s*[BM]?)", content, re.IGNORECASE
    )
    revenue = revenue_match.group(1) if revenue_match else "N/A"

    # Extract analyst rating
    rating_match = re.search(
        r"Consensus[^:]*Rating[^:]*:?\s*([\w\s]+)", content, re.IGNORECASE
    )
    rating = rating_match.group(1).strip() if rating_match else "N/A"

    # Extract price target
    target_match = re.search(
        r"Price Target[^:]*:?\s*\$?([\d,]+)", content, re.IGNORECASE
    )
    target = target_match.group(1) if target_match else "N/A"

    # Extract key strengths (count bullet points)
    strengths_match = re.search(
        r"## Key Strengths\s*(.*?)\s*##", content, re.DOTALL
    )
    num_strengths = len(re.findall(r"^\*\*", strengths_match.group(1), re.MULTILINE)) if strengths_match else 0

    # Extract key risks
    risks_match = re.search(r"## Key Risks[^:]*\s*(.*?)\s*##", content, re.DOTALL)
    num_risks = len(re.findall(r"^\*\*", risks_match.group(1), re.MULTILINE)) if risks_match else 0

    # Build summary
    key_points = []
    if revenue != "N/A":
        key_points.append(f"**Revenue:** ${revenue}")
    if rating != "N/A":
        key_points.append(f"**Analyst Rating:** {rating}")
    if target != "N/A":
        key_points.append(f"**Price Target:** ${target}")
    key_points.append(f"**Strengths:** {num_strengths} | **Risks:** {num_risks}")

    # Extract executive summary first paragraph
    exec_summary_match = re.search(
        r"## Executive Summary\s*(.*?)(?:##|\Z)", content, re.DOTALL
    )
    one_liner = "Fundamental analysis complete."
    if exec_summary_match:
        first_para = exec_summary_match.group(1).strip().split("\n\n")[0]
        one_liner = first_para[:200] + "..."

    return f"""## TL;DR Summary

**Ticker:** {ticker} | **Date:** {date} | **Report Type:** Fundamentals

### Key Points
{chr(10).join(f'- {point}' for point in key_points)}

### One-Line Summary
{one_liner}

---


"""


def extract_news_tldr(content: str, metadata: Dict[str, Any]) -> str:
    """Extract TL;DR from news analysis report."""
    ticker = metadata.get("ticker", "N/A")
    date = metadata.get("date", "N/A")

    # Count news items (look for headers or bullet points)
    news_items = re.findall(r"#{1,3}\s*(.*?)(?:\n|$)", content)
    news_count = len([n for n in news_items if len(n) > 5 and n[0] not in ("#", "*")])

    # Try to extract overall sentiment/impact
    impact_match = re.search(
        r"(?:Overall|Impact|Assessment)[^:]*:?\s*\*\*(.*?)\*\*", content, re.IGNORECASE
    )
    impact = impact_match.group(1) if impact_match else "Mixed"

    # Extract recent headlines (first few non-empty lines that look like headlines)
    headlines = []
    for line in content.split("\n")[:20]:
        line = line.strip()
        if line and not line.startswith("#") and len(line) > 20 and len(line) < 150:
            if any(keyword in line.lower() for keyword in ["report", "announce", "said", "plan", "deal"]):
                headlines.append(line[:80])
                if len(headlines) >= 3:
                    break

    key_points = [f"**News Items Analyzed:** {news_count}", f"**Overall Impact:** {impact}"]

    one_liner = f"News analysis for {ticker} covering {news_count} recent developments with {impact.lower()} impact."

    return f"""## TL;DR Summary

**Ticker:** {ticker} | **Date:** {date} | **Report Type:** News Analysis

### Key Points
{chr(10).join(f'- {point}' for point in key_points)}

### Key Headlines
{chr(10).join(f'- {h}' for h in headlines[:3])}

### One-Line Summary
{one_liner}

---


"""


def extract_sentiment_tldr(content: str, metadata: Dict[str, Any]) -> str:
    """Extract TL;DR from sentiment analysis report."""
    ticker = metadata.get("ticker", "N/A")
    date = metadata.get("date", "N/A")

    # Try to extract sentiment score
    score_match = re.search(
        r"(?:Sentiment|Score)[^:]*:?\s*([-\d.]+|%|[\w]+)", content, re.IGNORECASE
    )
    score = score_match.group(1) if score_match else "N/A"

    # Determine sentiment direction
    sentiment = "Neutral"
    if isinstance(score, str):
        score_upper = score.upper()
        if any(word in score_upper for word in ["POSITIVE", "BULLISH", "+", "HIGH"]):
            sentiment = "Positive"
        elif any(word in score_upper for word in ["NEGATIVE", "BEARISH", "-", "LOW"]):
            sentiment = "Negative"

    # Extract key themes
    themes_match = re.search(r"(?:Key Themes|Trending)[^:]*:?\s*(.*?)\s*##", content, re.DOTALL)
    themes = []
    if themes_match:
        themes = re.findall(r"[\*\-]\s*(.*?)(?:\n|$)", themes_match.group(1))[:3]

    key_points = [f"**Sentiment:** {sentiment}"]
    if score != "N/A":
        key_points.append(f"**Score:** {score}")

    one_liner = f"Sentiment analysis for {ticker} shows {sentiment.lower()} market perception."

    return f"""## TL;DR Summary

**Ticker:** {ticker} | **Date:** {date} | **Report Type:** Sentiment Analysis

### Key Points
{chr(10).join(f'- {point}' for point in key_points)}

### Key Themes
{chr(10).join(f'- {t.strip()}' for t in themes[:3]) if themes else '- Analysis based on social media and news sentiment'}

### One-Line Summary
{one_liner}

---


"""


def extract_investment_plan_tldr(content: str, metadata: Dict[str, Any]) -> str:
    """Extract TL;DR from investment plan (after research debate)."""
    ticker = metadata.get("ticker", "N/A")
    date = metadata.get("date", "N/A")

    # Extract recommendation (look for bolded BUY/SELL/HOLD)
    rec_match = re.search(r"\*\*(BUY|SELL|HOLD)\*\*", content, re.IGNORECASE)
    recommendation = rec_match.group(1).upper() if rec_match else "HOLD"

    # Extract entry points
    entry_match = re.search(
        r"(?:Entry|Initial Entry)[^:]*:?\s*(?:\$?[\d.]+|-?\s*at\s*\$?([\d.]+))",
        content, re.IGNORECASE
    )
    entry = entry_match.group(1) if entry_match else "N/A"

    # Extract stop loss
    stop_match = re.search(
        r"(?:Stop[- ]?Loss|Stop)[^:]*:?\s*\$?([\d.]+)", content, re.IGNORECASE
    )
    stop = stop_match.group(1) if stop_match else "N/A"

    # Extract target
    target_match = re.search(
        r"(?:Target|upside)[^:]*:?\s*\$?([\d.]+)", content, re.IGNORECASE
    )
    target = target_match.group(1) if target_match else "N/A"

    # Extract key arguments (bull vs bear summary)
    bull_bear_match = re.search(
        r"Bull[^:]*:(.*?)Bear[^:]*:(.*?)(?:My|The|##)", content, re.DOTALL | re.IGNORECASE
    )

    key_points = [f"**Recommendation:** {recommendation}"]
    if entry != "N/A":
        key_points.append(f"**Entry:** ${entry}")
    if stop != "N/A":
        key_points.append(f"**Stop:** ${stop}")
    if target != "N/A":
        key_points.append(f"**Target:** ${target}")

    # Get first paragraph as one-liner
    first_para = content.strip().split("\n\n")[0][:200]
    one_liner = first_para if first_para else f"Investment plan recommendation: {recommendation}"

    return f"""## TL;DR Summary

**Ticker:** {ticker} | **Date:** {date} | **Report Type:** Investment Plan

### Key Points
{chr(10).join(f'- {point}' for point in key_points)}

### One-Line Summary
{one_liner}

---


"""


def extract_trader_plan_tldr(content: str, metadata: Dict[str, Any]) -> str:
    """Extract TL;DR from trader investment plan."""
    ticker = metadata.get("ticker", "N/A")
    date = metadata.get("date", "N/A")

    # Extract final transaction proposal
    rec_match = re.search(
        r"FINAL TRANSACTION PROPOSAL:\s*\*\*(BUY|SELL|HOLD)\*\*", content, re.IGNORECASE
    )
    recommendation = rec_match.group(1).upper() if rec_match else "HOLD"

    # Extract agreement/concurrence
    concur_match = re.search(r"(?:concur|agree)[^:]*:\s*(.*?)(?:\.|\n)", content, re.IGNORECASE)
    concur = concur_match.group(1).strip()[:100] if concur_match else ""

    key_points = [f"**Decision:** {recommendation}"]
    if concur:
        key_points.append(f"**Rationale:** {concur}...")

    # Get first paragraph as one-liner
    first_para = content.strip().split("\n\n")[0][:200]
    one_liner = first_para if first_para else f"Trader decision: {recommendation}"

    return f"""## TL;DR Summary

**Ticker:** {ticker} | **Date:** {date} | **Report Type:** Trader Decision

### Key Points
{chr(10).join(f'- {point}' for point in key_points)}

### One-Line Summary
{one_liner}

---


"""


def extract_final_decision_tldr(content: str, metadata: Dict[str, Any]) -> str:
    """Extract TL;DR from final trade decision (after risk debate)."""
    ticker = metadata.get("ticker", "N/A")
    date = metadata.get("date", "N/A")

    # Remove escape characters for dollar signs
    content_clean = content.replace(r"\$", "$")

    # Extract recommendation (usually at top)
    rec_match = re.search(r"\*\*Recommendation:\s*(Buy|Sell|Hold)\*\*", content_clean, re.IGNORECASE)
    recommendation = rec_match.group(1).upper() if rec_match else "HOLD"

    # Extract entry from the entry line or from percentage position
    entry_match = re.search(
        r"(?:Initial Entry|Immediate Execution)[^(]*?(?:at\s+\$?([\d.]+)|current levels)",
        content_clean, re.IGNORECASE
    )
    if not entry_match:
        # Fallback: look for any dollar amount near "Entry"
        entry_match = re.search(
            r"Entry[^\$]*\$?([\d.]+)", content_clean, re.IGNORECASE
        )
    entry = entry_match.group(1) if entry_match else "See report"

    # Extract stop loss - look for patterns like "$230.00"
    stop_match = re.search(
        r"Stop[- ]?Loss[^\$]*\$?([\d.]+)", content_clean, re.IGNORECASE
    )
    if not stop_match:
        stop_match = re.search(
            r"stop[^:]*\$?([\d.]+)", content_clean, re.IGNORECASE
        )
    stop = stop_match.group(1) if stop_match else "N/A"

    # Extract target - look for patterns
    target_match = re.search(
        r"(?:Target|Breakout|upside)[^\$]*\$?([\d.]+)", content_clean, re.IGNORECASE
    )
    if not target_match:
        target_match = re.search(
            r"to\s+\$?([\d.]+)\s+(?:for|signals|confirms)", content_clean, re.IGNORECASE
        )
    target = target_match.group(1) if target_match else "N/A"

    # Extract summary of key arguments
    arguments_summary = []
    risky_match = re.search(
        r"\*\*Risky Analyst[^:]*:\*\*\s*(.*?)(?=\*\*|\n\n)", content_clean, re.DOTALL
    )
    if risky_match:
        arg = risky_match.group(1).strip()[:100]
        arguments_summary.append(f"**Bull:** {arg}...")

    safe_match = re.search(
        r"\*\*(?:Conservative|Safe) Analyst[^:]*:\*\*\s*(.*?)(?=\*\*|\n\n)", content_clean, re.DOTALL
    )
    if safe_match:
        arg = safe_match.group(1).strip()[:100]
        arguments_summary.append(f"**Bear:** {arg}...")

    # Extract rationale section
    rationale_match = re.search(
        r"### Rationale\s*(.*?)(?:###|\Z)", content_clean, re.DOTALL
    )
    one_liner = f"Final decision: {recommendation}"
    if rationale_match:
        one_liner = rationale_match.group(1).strip().split(".")[0][:200]

    key_points = [f"**Final Decision:** {recommendation}"]
    if entry != "N/A":
        key_points.append(f"**Entry:** ${entry}" if entry != "See report" else f"**Entry:** {entry}")
    if stop != "N/A":
        key_points.append(f"**Stop:** ${stop}")
    if target != "N/A":
        key_points.append(f"**Target:** ${target}")

    return f"""## TL;DR Summary

**Ticker:** {ticker} | **Date:** {date} | **Report Type:** Final Trade Decision

### Key Points
{chr(10).join(f'- {point}' for point in key_points)}

### Key Arguments
{chr(10).join(f'- {arg}' for arg in arguments_summary[:3])}

### One-Line Summary
{one_liner}

---


"""


def extract_generic_tldr(content: str, metadata: Dict[str, Any]) -> str:
    """Generic TL;DR extraction for unknown report types."""
    ticker = metadata.get("ticker", "N/A")
    date = metadata.get("date", "N/A")
    report_type = metadata.get("report_type", "Report")

    # Get first few non-empty lines
    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
    preview = " ".join(lines[:3])[:200]

    return f"""## TL;DR Summary

**Ticker:** {ticker} | **Date:** {date} | **Report Type:** {report_type}

### Preview
{preview}...

---


"""
