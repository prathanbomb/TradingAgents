"""RQ task functions for running analysis jobs."""

import json
import logging
import uuid
from pathlib import Path

from tradingagents.api.job_store import JobStore

logger = logging.getLogger(__name__)


def run_analysis(
    job_id: str,
    ticker: str,
    trade_date: str,
    config_snapshot: dict | None = None,
    db_path: str = "./data/jobs.db",
):
    """RQ task: run trading analysis for a single ticker.

    This is executed by the RQ worker process.
    """
    store = JobStore(db_path=db_path)

    try:
        store.update_status(job_id, "running")

        from tradingagents.config.models import TradingAgentsConfig
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.config import StorageConfig
        from tradingagents.storage import StorageService

        # Build config from snapshot or env
        if config_snapshot:
            config = TradingAgentsConfig.from_legacy_dict(config_snapshot)
        else:
            config = TradingAgentsConfig.from_env()

        # Handle direct API key (same pattern as run_scheduled_analysis.py)
        import os
        if api_key := os.getenv("LLM_API_KEY"):
            config_dict = config.to_legacy_dict()
            config_dict["api_key_env_var"] = f"__DIRECT_KEY__:{api_key}"
            config = TradingAgentsConfig.from_legacy_dict(config_dict)

        # Run analysis
        graph = TradingAgentsGraph(
            selected_analysts=["market", "social", "news", "fundamentals"],
            config=config,
            debug=False,
        )
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

        # Save reports via storage service
        storage_config = StorageConfig.from_env()
        report_paths = {}
        if storage_config.local_path or storage_config.is_r2_enabled:
            storage = StorageService(storage_config)
            prefix = f"{ticker}_{trade_date}_{job_id[:8]}"
            for name, content in reports.items():
                if not content:
                    continue
                key = f"{prefix}/{name}.md"
                paths = storage.upload_report_auto(content, key, content_type="text/markdown")
                report_paths[name] = {
                    "paths": paths,
                    "url": storage.get_report_url(key),
                }

        # Send Discord notification
        _send_discord(ticker, trade_date, decision, report_paths)

        # Update job as completed
        store.update_status(
            job_id,
            "completed",
            result={"decision": decision, "state_key": f"{ticker}_{trade_date}_{job_id[:8]}"},
            reports=report_paths if report_paths else None,
        )

        logger.info(f"Job {job_id} completed: {ticker} -> {decision}")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        try:
            store.update_status(job_id, "failed", error=str(e))
        except Exception:
            logger.error(f"Failed to update job {job_id} status to failed")


def _send_discord(ticker: str, trade_date: str, decision: str, reports: dict):
    """Send Discord notification (best-effort)."""
    import os
    import requests as http_requests

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return

    decision_upper = decision.upper() if decision else "UNKNOWN"
    if "BUY" in decision_upper:
        color = 0x00FF00
    elif "SELL" in decision_upper:
        color = 0xFF0000
    else:
        color = 0xFFFF00

    report_links = []
    for name, info in reports.items():
        url = info.get("url")
        if url:
            display_name = name.replace("_", " ").title()
            report_links.append(f"- [{display_name}]({url})")

    fields = [
        {"name": "Date", "value": trade_date, "inline": True},
        {"name": "Decision", "value": decision or "N/A", "inline": True},
    ]
    if report_links:
        fields.append({"name": "Reports", "value": "\n".join(report_links[:5]), "inline": False})

    from datetime import datetime, timezone
    embed = {
        "title": f"Trading Analysis: {ticker}",
        "color": color,
        "fields": fields,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        http_requests.post(
            webhook_url,
            json={"embeds": [embed]},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
    except Exception:
        pass
