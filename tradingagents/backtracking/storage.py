"""Storage management for prediction records.

This module provides a high-level interface for storing and retrieving
prediction records and performance data.
"""

import logging
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from .agent_tracker import AgentTracker, PredictionRecord
from .performance import PerformanceMetrics, PerformanceReport

logger = logging.getLogger(__name__)


class PerformanceStorage:
    """Storage and retrieval interface for performance data.

    This class provides methods for:
    - Tracking predictions from trading analyses
    - Fetching price data for outcome calculation
    - Generating performance reports
    - Managing historical performance data
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize performance storage.

        Args:
            storage_path: Path to store prediction records. Defaults to ./data/predictions/
        """
        self.tracker = AgentTracker(storage_path)
        self.metrics = PerformanceMetrics()

    def record_prediction_from_state(
        self,
        ticker: str,
        trade_date: str,
        final_state: Dict[str, Any],
        decision: str,
    ) -> PredictionRecord:
        """Record a prediction from a completed trading graph run.

        This is typically called immediately after graph.propagate() returns.

        Args:
            ticker: Stock ticker symbol
            trade_date: Trade date (YYYY-MM-DD)
            final_state: Final state from graph.propagate()
            decision: Final decision string (BUY/SELL/HOLD)

        Returns:
            PredictionRecord that was saved
        """
        return self.tracker.record_prediction(ticker, trade_date, final_state, decision)

    def update_outcomes_for_ticker(
        self,
        ticker: str,
        hold_days: int = 7,
        force_refresh: bool = False,
    ) -> int:
        """Update outcomes for all predictions of a ticker that haven't been calculated yet.

        This fetches price data and calculates returns for each prediction.

        Args:
            ticker: Stock ticker symbol
            hold_days: Number of days to hold for return calculation
            force_refresh: Re-calculate outcomes even if already calculated

        Returns:
            Number of predictions updated
        """
        from tradingagents.dataflows.interface import route_to_vendor
        import pandas as pd
        from io import StringIO

        # Get all predictions for this ticker
        records = self.tracker.load_predictions(ticker=ticker)

        if not records:
            logger.info(f"No predictions found for {ticker}")
            return 0

        updated_count = 0

        for record in records:
            # Skip if already calculated and not forcing refresh
            if record.outcome_calculated and not force_refresh:
                continue

            try:
                # Calculate target date
                trade_date = pd.to_datetime(record.trade_date)
                target_date = trade_date + timedelta(days=hold_days)
                end_date = target_date + timedelta(days=7)  # Add buffer for weekends

                # Fetch price data
                price_data = route_to_vendor(
                    "get_stock_data",
                    ticker,
                    record.trade_date,
                    end_date.strftime("%Y-%m-%d"),
                )

                if not price_data:
                    logger.warning(f"No price data available for {ticker} from {record.trade_date}")
                    continue

                # Parse price data
                df = pd.read_csv(StringIO(price_data))
                df['Date'] = pd.to_datetime(df['Date'])

                # Find trade date price (use closest available)
                trade_row = df.iloc[(df['Date'] - trade_date).abs().argsort()[:1]]
                if trade_row.empty:
                    logger.warning(f"No price found for {ticker} near {record.trade_date}")
                    continue
                entry_price = trade_row['Close'].iloc[0]

                # Find target date price
                target_rows = df[df['Date'] >= target_date]
                if target_rows.empty:
                    logger.warning(f"No price found for {ticker} after {target_date.date()}")
                    continue
                exit_price = target_rows.iloc[0]['Close']

                # Update the record
                self.tracker.update_outcome(
                    ticker=ticker,
                    trade_date=record.trade_date,
                    entry_price=float(entry_price),
                    exit_price=float(exit_price),
                    hold_days=hold_days,
                )
                updated_count += 1

            except Exception as e:
                logger.error(f"Failed to update outcome for {ticker} on {record.trade_date}: {e}")
                continue

        logger.info(f"Updated outcomes for {updated_count} predictions of {ticker}")
        return updated_count

    def generate_performance_report(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> PerformanceReport:
        """Generate a performance report.

        Args:
            ticker: Filter by ticker (if None, include all)
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)

        Returns:
            PerformanceReport with calculated metrics
        """
        # Load records with outcomes
        records = self.tracker.load_predictions(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

        # Filter to only include records with calculated outcomes
        records_with_outcomes = [r for r in records if r.outcome_calculated]

        if not records_with_outcomes:
            logger.warning("No records with outcomes found for performance report")
            return PerformanceReport(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
            )

        # Calculate performance for all agent types
        agent_performances = self.metrics.calculate_all_agent_performance(records_with_outcomes)

        # Calculate bull vs bear comparison
        bull_vs_bear = self.metrics.calculate_bull_vs_bear_performance(records_with_outcomes)

        # Calculate overall metrics
        final_perfs = [p for p in agent_performances.values() if p.total_predictions > 0]
        overall_accuracy = statistics.mean([p.accuracy for p in final_perfs]) if final_perfs else 0.0
        overall_avg_return = statistics.mean([p.avg_return for p in final_perfs]) if final_perfs else 0.0

        return PerformanceReport(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            total_predictions=len(records_with_outcomes),
            agent_performances=agent_performances,
            bull_vs_bear=bull_vs_bear,
            overall_accuracy=overall_accuracy,
            overall_avg_return=overall_avg_return,
        )

    def get_leaderboard(self, metric: str = "avg_return") -> List[tuple]:
        """Get agent rankings by performance metric.

        Args:
            metric: Metric to rank by ("accuracy", "avg_return", "sharpe_ratio", "win_rate")

        Returns:
            List of (agent_name, metric_value) tuples, sorted highest to lowest
        """
        report = self.generate_performance_report()

        leaderboard = []
        for agent_name, perf in report.agent_performances.items():
            value = getattr(perf, metric, None)
            if value is not None:
                leaderboard.append((agent_name, value))

        # Sort highest to lowest
        leaderboard.sort(key=lambda x: x[1], reverse=True)
        return leaderboard

    def export_performance_data(
        self,
        output_path: Path,
        format: str = "json",
    ) -> None:
        """Export all performance data to a file.

        Args:
            output_path: Path to save the export
            format: Export format ("json" or "csv")
        """
        records = self.tracker.load_predictions()

        if format == "json":
            data = {
                "records": [r.to_dict() for r in records],
                "generated_at": datetime.utcnow().isoformat(),
            }
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)

        elif format == "csv":
            import pandas as pd
            df = pd.DataFrame([r.to_dict() for r in records])
            df.to_csv(output_path, index=False)

        else:
            raise ValueError(f"Unsupported export format: {format}")

        logger.info(f"Exported performance data to {output_path}")

    def get_prediction_history(
        self,
        ticker: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent prediction history for a ticker.

        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of predictions to return

        Returns:
            List of prediction dictionaries
        """
        records = self.tracker.load_predictions(ticker=ticker)[:limit]

        return [
            {
                "date": r.trade_date,
                "final_signal": r.final_signal.value,
                "return_pct": r.return_pct,
                "correct": r.final_correct,
            }
            for r in records
        ]
