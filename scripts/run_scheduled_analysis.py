#!/usr/bin/env python3
"""Scheduled analysis script for GitHub Actions.

Reads tickers from tickers.txt and runs analysis for each one.
Reports are saved to R2 storage with public URLs.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.config import StorageConfig
from tradingagents.storage import StorageService

# PDF conversion is optional (requires system dependencies like pango, gobject)
try:
    from tradingagents.storage.pdf import convert_reports_to_pdf
    PDF_AVAILABLE = True
except (ImportError, OSError):
    PDF_AVAILABLE = False
    convert_reports_to_pdf = None


def load_tickers(filepath: str = "tickers.txt") -> list[str]:
    """Load tickers from file, ignoring comments and empty lines."""
    tickers = []
    path = Path(__file__).parent.parent / filepath

    if not path.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                tickers.append(line.upper())

    return tickers


def build_config() -> dict:
    """Build configuration from environment variables."""
    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1

    if llm_provider := os.getenv("LLM_PROVIDER"):
        config["llm_provider"] = llm_provider

    if deep_think_model := os.getenv("LLM_DEEP_THINK_MODEL"):
        config["deep_think_llm"] = deep_think_model

    if quick_think_model := os.getenv("LLM_QUICK_THINK_MODEL"):
        config["quick_think_llm"] = quick_think_model

    if backend_url := os.getenv("LLM_BACKEND_URL"):
        config["backend_url"] = backend_url

    if api_key := os.getenv("LLM_API_KEY"):
        config["api_key_env_var"] = f"__DIRECT_KEY__:{api_key}"

    if embedding_provider := os.getenv("EMBEDDING_PROVIDER"):
        config["embedding_provider"] = embedding_provider

    if embedding_model := os.getenv("EMBEDDING_MODEL"):
        config["embedding_model"] = embedding_model

    if embedding_backend_url := os.getenv("EMBEDDING_BACKEND_URL"):
        config["embedding_backend_url"] = embedding_backend_url

    return config


def save_reports(ticker: str, trade_date: str, reports: dict) -> dict | None:
    """Save reports to storage backends and convert to PDF."""
    storage_config = StorageConfig.from_env()

    if not storage_config.local_path and not storage_config.is_r2_enabled:
        print("  Warning: No storage configured")
        return None

    storage = StorageService(storage_config)
    job_id = uuid.uuid4().hex[:8]
    prefix = f"{ticker}_{trade_date}_{job_id}"
    report_results = {}

    for name, content in reports.items():
        if not content:
            continue

        md_key = f"{prefix}/{name}.md"
        paths = storage.upload_report(content, md_key, content_type="text/markdown")

        report_results[name] = {
            "paths": paths,
            "url": storage.get_report_url(md_key),
        }

    # Convert to PDF if available and local storage exists
    if PDF_AVAILABLE:
        local_dir = storage.get_local_path(prefix)
        if local_dir:
            local_path = Path(local_dir).parent / prefix
            if local_path.exists():
                pdf_paths = convert_reports_to_pdf(local_path)
                for pdf_path in pdf_paths:
                    pdf_key = f"{prefix}/{pdf_path.name}"
                    pdf_result = storage.upload_file(pdf_path, pdf_key)
                    report_name = pdf_path.stem
                    if report_name in report_results:
                        report_results[report_name]["pdf_paths"] = pdf_result
                        report_results[report_name]["pdf_url"] = storage.get_report_url(pdf_key)

    return {
        "prefix": prefix,
        "reports": report_results,
        "backends": storage.backends,
        "primary_backend": storage.primary_backend,
        "is_r2_enabled": storage.is_r2_enabled,
    }


def send_discord_notification(
    ticker: str, trade_date: str, decision: str, storage_result: dict | None
) -> bool:
    """Send Discord notification with analysis results and report links."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return False

    # Determine decision emoji
    decision_upper = decision.upper() if decision else "UNKNOWN"
    if "BUY" in decision_upper:
        decision_emoji = "📈"
        color = 0x00FF00  # Green
    elif "SELL" in decision_upper:
        decision_emoji = "📉"
        color = 0xFF0000  # Red
    else:
        decision_emoji = "⏸️"
        color = 0xFFFF00  # Yellow

    # Build report links
    report_links = []
    if storage_result and storage_result.get("reports"):
        reports = storage_result["reports"]
        # Prioritize final decision and investment plan
        priority_reports = ["final_trade_decision", "investment_plan", "trader_investment_plan"]
        for report_name in priority_reports:
            if report_name in reports:
                report = reports[report_name]
                url = report.get("pdf_url") or report.get("url")
                if url:
                    display_name = report_name.replace("_", " ").title()
                    report_links.append(f"• [{display_name}]({url})")

    # Build embed
    embed = {
        "title": f"📊 Trading Analysis: {ticker}",
        "color": color,
        "fields": [
            {"name": "📅 Date", "value": trade_date, "inline": True},
            {"name": f"{decision_emoji} Decision", "value": decision or "N/A", "inline": True},
        ],
        "footer": {"text": "TradingAgents"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if report_links:
        embed["fields"].append({
            "name": "📄 Reports",
            "value": "\n".join(report_links),
            "inline": False,
        })

    payload = {"embeds": [embed]}

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        print("  Discord notification sent")
        return True
    except Exception as e:
        print(f"  Discord notification failed: {e}")
        return False


def run_analysis(ticker: str, trade_date: str, config: dict) -> dict | None:
    """Run analysis for a single ticker."""
    print(f"\n{'='*60}")
    print(f"Analyzing {ticker} for {trade_date}")
    print(f"{'='*60}")

    try:
        # Create graph with all analysts
        graph = TradingAgentsGraph(
            selected_analysts=["market", "social", "news", "fundamentals"],
            config=config,
            debug=False,
        )

        # Run analysis
        print("  Running analysis...")
        final_state, decision = graph.propagate(ticker, trade_date)

        # Extract reports
        reports = {
            "market_report": final_state.get("market_report", ""),
            "sentiment_report": final_state.get("sentiment_report", ""),
            "news_report": final_state.get("news_report", ""),
            "fundamentals_report": final_state.get("fundamentals_report", ""),
            "investment_plan": final_state.get("investment_plan", ""),
            "trader_investment_plan": final_state.get("trader_investment_plan", ""),
            "final_trade_decision": final_state.get("final_trade_decision", ""),
        }

        # Save reports
        print("  Saving reports...")
        storage_result = save_reports(ticker, trade_date, reports)

        # Send Discord notification
        send_discord_notification(ticker, trade_date, decision, storage_result)

        print(f"  Decision: {decision}")

        return {
            "ticker": ticker,
            "trade_date": trade_date,
            "decision": decision,
            "storage": storage_result,
        }

    except Exception as e:
        print(f"  Error: {e}")
        return None


def main():
    """Main entry point."""
    print("=" * 60)
    print("Trading Agents - Scheduled Analysis")
    print("=" * 60)

    # Check for custom tickers from environment (workflow_dispatch or repository_dispatch)
    custom_tickers = os.environ.get("CUSTOM_TICKERS", "").strip()
    if custom_tickers:
        tickers = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]
        print(f"\nUsing custom tickers: {', '.join(tickers)}")
    else:
        tickers = load_tickers()
        print(f"\nTickers from tickers.txt: {', '.join(tickers)}")

    # Get today's date
    trade_date = datetime.now().strftime("%Y-%m-%d")
    print(f"Trade date: {trade_date}")

    # Build config
    config = build_config()
    print(f"LLM Provider: {config.get('llm_provider', 'openai')}")

    # Run analysis for each ticker
    results = []
    for ticker in tickers:
        result = run_analysis(ticker, trade_date, config)
        if result:
            results.append(result)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for result in results:
        ticker = result["ticker"]
        decision = result["decision"]
        storage = result.get("storage", {})

        print(f"\n{ticker}: {decision}")

        if storage and storage.get("reports"):
            final_report = storage["reports"].get("final_trade_decision", {})
            if url := final_report.get("pdf_url") or final_report.get("url"):
                print(f"  Report: {url}")

    print(f"\nCompleted: {len(results)}/{len(tickers)} tickers")

    # Exit with error if any failed
    if len(results) < len(tickers):
        sys.exit(1)


if __name__ == "__main__":
    main()
