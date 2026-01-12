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

# Performance tracking (optional - will be available in full version)
try:
    from tradingagents.backtracking import PerformanceStorage
    PERFORMANCE_AVAILABLE = True
except ImportError:
    PERFORMANCE_AVAILABLE = False

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

    # Metadata for TL;DR generation
    metadata = {
        "ticker": ticker,
        "date": trade_date,
    }

    for name, content in reports.items():
        if not content:
            continue

        md_key = f"{prefix}/{name}.md"
        # Use upload_report_auto to automatically add TL;DR if configured
        paths = storage.upload_report_auto(
            content, md_key, metadata=metadata, content_type="text/markdown"
        )

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

        # Track prediction for performance analysis
        if PERFORMANCE_AVAILABLE:
            try:
                perf_storage = PerformanceStorage()
                perf_storage.record_prediction_from_state(
                    ticker=ticker,
                    trade_date=trade_date,
                    final_state=final_state,
                    decision=decision,
                )
                print("  Prediction recorded for performance tracking")
            except Exception as e:
                print(f"  Warning: Could not record prediction: {e}")

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


def update_performance_outcomes(tickers: list[str], hold_days: int = 7) -> None:
    """Update outcomes for past predictions that haven't been calculated yet.

    This fetches current price data and calculates returns for predictions
    that were made in the past.

    Args:
        tickers: List of ticker symbols to update
        hold_days: Number of days to hold for return calculation
    """
    if not PERFORMANCE_AVAILABLE:
        print("Performance tracking not available")
        return

    print("\n" + "=" * 60)
    print("UPDATING PERFORMANCE OUTCOMES")
    print("=" * 60)

    perf_storage = PerformanceStorage()
    total_updated = 0

    for ticker in tickers:
        print(f"\nUpdating outcomes for {ticker}...")
        try:
            updated = perf_storage.update_outcomes_for_ticker(
                ticker=ticker,
                hold_days=hold_days,
                force_refresh=False,
            )
            print(f"  Updated {updated} predictions")
            total_updated += updated
        except Exception as e:
            print(f"  Error updating {ticker}: {e}")

    print(f"\nTotal predictions updated: {total_updated}")


def generate_performance_report(ticker: str = None, days: int = 30) -> None:
    """Generate and display a performance report.

    Args:
        ticker: Filter by specific ticker (None = all tickers)
        days: Number of recent days to include in report
    """
    if not PERFORMANCE_AVAILABLE:
        print("Performance tracking not available")
        return

    print("\n" + "=" * 60)
    print("PERFORMANCE REPORT")
    print("=" * 60)

    perf_storage = PerformanceStorage()

    # Calculate end date (today) and start date
    from datetime import timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        report = perf_storage.generate_performance_report(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

        # Display summary
        print(report.generate_summary())
        print("")

        # Display full report if there's data
        if report.agent_performances:
            print(report.generate_markdown())

            # Save report to file
            reports_dir = Path("./reports/performance")
            reports_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{ticker or 'all'}_{timestamp}.md"
            filepath = reports_dir / filename

            with open(filepath, "w") as f:
                f.write(report.generate_markdown())

            print(f"\nReport saved to: {filepath}")

    except Exception as e:
        print(f"Error generating report: {e}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="TradingAgents - Multi-Agent Financial Trading Framework",
        epilog="Examples: %(prog)s --performance-report --ticker AAPL"
    )
    parser.add_argument(
        "--performance-report",
        action="store_true",
        help="Generate performance report for tracked predictions"
    )
    parser.add_argument(
        "--update-outcomes",
        action="store_true",
        help="Update outcomes for past predictions with current price data"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        help="Ticker symbol for performance report (default: all tickers)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to include in performance report (default: 30)"
    )

    args = parser.parse_args()

    # Handle performance reporting mode
    if args.performance_report:
        generate_performance_report(ticker=args.ticker, days=args.days)
        return

    # Handle outcome update mode
    if args.update_outcomes:
        tickers = [args.ticker] if args.ticker else load_tickers()
        update_performance_outcomes(tickers)
        return

    # Normal analysis mode
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
