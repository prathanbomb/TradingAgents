"""Confidence history query interface and trend analysis.

This module provides ConfidenceHistory for querying and analyzing confidence
data over time, including summary statistics, trend analysis, and calibration
integration.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np

from tradingagents.observability.confidence.calibration import CalibrationMetrics
from tradingagents.observability.models.decision_record import DecisionRecord

if TYPE_CHECKING:
    from tradingagents.observability.storage.sqlite_backend import SQLiteDecisionStore

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceSummary:
    """Summary statistics for confidence data.

    Attributes:
        avg_confidence: Average confidence across all records
        min_confidence: Minimum confidence
        max_confidence: Maximum confidence
        std_confidence: Standard deviation of confidence
        sample_count: Number of records
        system_avg_confidence: Average system confidence
        agent_avg_confidences: Per-agent average confidences
    """

    avg_confidence: float
    min_confidence: float
    max_confidence: float
    std_confidence: float
    sample_count: int
    system_avg_confidence: float
    agent_avg_confidences: Dict[str, float]


@dataclass
class ConfidenceTrend:
    """Confidence trend analysis results.

    Attributes:
        dates: Trade dates in chronological order
        confidences: Confidence values for each date
        system_confidences: System confidence values
        trend: Overall trend direction
        slope: Linear regression slope (confidence per day)
        correlation: Correlation coefficient for trend
    """

    dates: List[str]
    confidences: List[float]
    system_confidences: List[float]
    trend: str
    slope: float
    correlation: float


class ConfidenceHistory:
    """Query interface for confidence history and trend analysis.

    Provides methods for querying confidence data with filters, computing
    summary statistics, analyzing trends, and integrating with calibration
    metrics.

    Example:
        ```python
        history = ConfidenceHistory(store=store)

        # Query confidence history
        records = history.get_confidence_history(ticker='AAPL', confidence_min=0.7)

        # Get summary statistics
        summary = history.get_confidence_summary()

        # Analyze trend
        trend = history.get_confidence_trend(ticker='AAPL')
        ```
    """

    def __init__(self, store: Optional["SQLiteDecisionStore"] = None):
        """Initialize confidence history interface.

        Args:
            store: Optional SQLite storage backend. If None, creates default store.
        """
        if store is None:
            from tradingagents.observability.storage import get_decision_store
            store = get_decision_store()

        self.store = store
        logger.debug("ConfidenceHistory initialized")

    def get_confidence_history(
        self,
        ticker: Optional[str] = None,
        agent_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        confidence_min: Optional[float] = None,
        confidence_max: Optional[float] = None,
        include_system: bool = True,
        limit: int = 1000,
    ) -> List[DecisionRecord]:
        """Query decision records with confidence filters.

        Args:
            ticker: Optional ticker filter
            agent_type: Optional agent type filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            confidence_min: Optional minimum confidence threshold
            confidence_max: Optional maximum confidence threshold
            include_system: Whether to include system_confidence in filtering
            limit: Maximum number of records to return

        Returns:
            List of DecisionRecord objects sorted by trade_date DESC
        """
        records = self.store.get_decision_records_by_confidence(
            confidence_min=confidence_min,
            confidence_max=confidence_max,
            ticker=ticker,
            agent_type=agent_type,
            start_date=start_date,
            end_date=end_date,
            include_system_confidence=include_system,
            limit=limit,
        )

        # Convert dicts to DecisionRecord objects
        result = []
        for record_dict in records:
            try:
                result.append(DecisionRecord.from_dict(record_dict))
            except Exception as e:
                logger.warning(f"Failed to convert record to DecisionRecord: {e}")

        logger.debug(f"Retrieved {len(result)} confidence records")
        return result

    def get_confidence_summary(
        self,
        ticker: Optional[str] = None,
        agent_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ConfidenceSummary:
        """Compute summary statistics for confidence data.

        Args:
            ticker: Optional ticker filter
            agent_type: Optional agent type filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Returns:
            ConfidenceSummary with aggregate statistics
        """
        records = self.get_confidence_history(
            ticker=ticker,
            agent_type=agent_type,
            start_date=start_date,
            end_date=end_date,
            limit=10000,
        )

        if not records:
            return ConfidenceSummary(
                avg_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                std_confidence=0.0,
                sample_count=0,
                system_avg_confidence=0.0,
                agent_avg_confidences={},
            )

        # Extract confidence values
        confidences = [r.confidence for r in records if r.confidence is not None]
        system_confidences = [
            r.system_confidence for r in records if r.system_confidence is not None
        ]

        if not confidences:
            return ConfidenceSummary(
                avg_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
                std_confidence=0.0,
                sample_count=len(records),
                system_avg_confidence=0.0,
                agent_avg_confidences={},
            )

        # Compute statistics
        conf_array = np.array(confidences)
        avg_confidence = float(np.mean(conf_array))
        min_confidence = float(np.min(conf_array))
        max_confidence = float(np.max(conf_array))
        std_confidence = float(np.std(conf_array))

        system_avg = (
            float(np.mean(system_confidences)) if system_confidences else 0.0
        )

        # Per-agent averages
        agent_avgs = self._compute_agent_averages(records)

        return ConfidenceSummary(
            avg_confidence=avg_confidence,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            std_confidence=std_confidence,
            sample_count=len(records),
            system_avg_confidence=system_avg,
            agent_avg_confidences=agent_avgs,
        )

    def _compute_agent_averages(
        self, records: List[DecisionRecord]
    ) -> Dict[str, float]:
        """Compute average confidence per agent.

        Args:
            records: List of DecisionRecord objects

        Returns:
            Dict mapping agent_name to average confidence
        """
        agent_confidences: Dict[str, List[float]] = {}

        for record in records:
            if record.confidence is not None:
                if record.agent_name not in agent_confidences:
                    agent_confidences[record.agent_name] = []
                agent_confidences[record.agent_name].append(record.confidence)

        return {
            agent: float(np.mean(confs))
            for agent, confs in agent_confidences.items()
            if confs
        }

    def get_confidence_trend(
        self,
        ticker: str,
        agent_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_system_confidence: bool = True,
    ) -> ConfidenceTrend:
        """Analyze confidence changes over time.

        Args:
            ticker: Ticker symbol to analyze
            agent_type: Optional agent type filter
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            use_system_confidence: Whether to use system_confidence for trend

        Returns:
            ConfidenceTrend with dates, confidences, and trend analysis
        """
        # Get time series data from storage
        series = self.store.get_confidence_time_series(
            ticker=ticker,
            agent_type=agent_type,
            start_date=start_date,
            end_date=end_date,
        )

        if not series:
            return ConfidenceTrend(
                dates=[],
                confidences=[],
                system_confidences=[],
                trend="stable",
                slope=0.0,
                correlation=0.0,
            )

        # Extract data
        dates = [item[0] for item in series]
        confidences = [item[1] if item[1] is not None else 0.5 for item in series]
        system_confidences = [
            item[2] if item[2] is not None else 0.5 for item in series
        ]

        # Use system or individual confidence
        values = system_confidences if use_system_confidence else confidences

        # Compute trend
        slope, correlation, trend = compute_trend_slope(dates, values)

        return ConfidenceTrend(
            dates=dates,
            confidences=confidences,
            system_confidences=system_confidences,
            trend=trend,
            slope=slope,
            correlation=correlation,
        )

    def get_calibration_summary(
        self, agent_name: Optional[str] = None
    ) -> CalibrationMetrics:
        """Get calibration metrics from storage.

        Args:
            agent_name: Optional agent name for per-agent calibration

        Returns:
            CalibrationMetrics with ECE, Brier score, etc.
        """
        return self.store.get_calibration_metrics(agent_name=agent_name)

    def get_high_confidence_decisions(
        self,
        ticker: Optional[str] = None,
        threshold: float = 0.8,
        limit: int = 100,
    ) -> List[DecisionRecord]:
        """Get decisions with confidence >= threshold.

        Useful for assessing "high confidence" reliability.

        Args:
            ticker: Optional ticker filter
            threshold: Minimum confidence threshold
            limit: Maximum number of records to return

        Returns:
            List of DecisionRecord objects with high confidence
        """
        return self.get_confidence_history(
            ticker=ticker, confidence_min=threshold, limit=limit
        )

    def get_low_confidence_decisions(
        self,
        ticker: Optional[str] = None,
        threshold: float = 0.5,
        limit: int = 100,
    ) -> List[DecisionRecord]:
        """Get decisions with confidence < threshold.

        Useful for identifying uncertain decisions.

        Args:
            ticker: Optional ticker filter
            threshold: Maximum confidence threshold
            limit: Maximum number of records to return

        Returns:
            List of DecisionRecord objects with low confidence
        """
        return self.get_confidence_history(
            ticker=ticker, confidence_max=threshold, limit=limit
        )


def compute_trend_slope(
    dates: List[str], confidences: List[float]
) -> Tuple[float, float, str]:
    """Perform linear regression on time series.

    Args:
        dates: List of date strings (YYYY-MM-DD)
        confidences: List of confidence values

    Returns:
        Tuple of (slope, correlation, trend_direction)
        - slope: Linear regression slope (confidence per day)
        - correlation: Correlation coefficient
        - trend_direction: "increasing", "decreasing", or "stable"
    """
    if len(dates) < 2:
        return 0.0, 0.0, "stable"

    try:
        # Convert dates to numeric values (days since epoch)
        date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        epoch = datetime(1970, 1, 1)
        x = np.array([(d - epoch).days for d in date_objects])
        y = np.array(confidences)

        # Perform linear regression
        slope, intercept = np.polyfit(x, y, 1)

        # Compute correlation
        if len(x) > 1:
            correlation = float(np.corrcoef(x, y)[0, 1])
        else:
            correlation = 0.0

        # Determine trend direction
        if abs(slope) < 1e-6:  # Essentially zero
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        return float(slope), float(correlation), trend

    except Exception as e:
        logger.error(f"Trend calculation failed: {e}")
        return 0.0, 0.0, "stable"


def group_by_agent(
    records: List[DecisionRecord], by_type: bool = False
) -> Dict[str, List[DecisionRecord]]:
    """Group records by agent_name or agent_type.

    Args:
        records: List of DecisionRecord objects
        by_type: If True, group by agent_type instead of agent_name

    Returns:
        Dict mapping agent identifier to list of DecisionRecord objects
    """
    grouped: Dict[str, List[DecisionRecord]] = {}

    for record in records:
        key = record.agent_type if by_type else record.agent_name
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(record)

    return grouped
