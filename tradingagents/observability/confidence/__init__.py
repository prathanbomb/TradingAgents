"""Confidence scoring module for agent decision confidence.

This module provides confidence estimation methods for agent outputs,
including verbalized confidence parsing, ensemble consistency scoring,
and token probability extraction. Also includes aggregation methods
for combining multiple agent confidences into system-level confidence,
and calibration tracking for assessing confidence reliability over time.

Confidence history query interface provides transparency into confidence
patterns, enabling users to assess reliability and identify trends.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tradingagents.observability.storage.sqlite_backend import SQLiteDecisionStore

from tradingagents.observability.confidence.aggregation import (
    ConfidenceAggregator,
    bayesian_aggregate,
    consensus_minimum,
    weighted_average,
)
from tradingagents.observability.confidence.calibration import (
    CalibrationMetrics,
    CalibrationTracker,
    calculate_ece,
)
from tradingagents.observability.confidence.history import (
    ConfidenceHistory,
    ConfidenceSummary,
    ConfidenceTrend,
    compute_trend_slope,
    group_by_agent,
)
from tradingagents.observability.confidence.models import AgentConfidence, ConfidenceMetadata
from tradingagents.observability.confidence.scorer import (
    ConfidenceScorer,
    calculate_ensemble_confidence,
    extract_token_confidence,
    extract_verbalized_confidence,
)
from tradingagents.observability.models.decision_record import DecisionRecord


# Factory functions for convenience


def create_calibration_tracker(agent_name: Optional[str] = None) -> CalibrationTracker:
    """Create a CalibrationTracker instance.

    Factory function for creating calibration trackers, following
    existing patterns from the confidence module.

    Args:
        agent_name: Optional agent name for per-agent tracking

    Returns:
        CalibrationTracker instance
    """
    return CalibrationTracker(agent_name=agent_name)


def compute_system_calibration(
    decision_records: List[DecisionRecord], outcomes: List[bool]
) -> CalibrationMetrics:
    """Compute system-level calibration from DecisionRecord list.

    Extracts system_confidence from records with outcomes and
    computes calibration metrics.

    Args:
        decision_records: List of DecisionRecord objects with confidence
        outcomes: List of boolean outcomes (True=correct, False=incorrect)

    Returns:
        CalibrationMetrics for system-level calibration

    Raises:
        ValueError: If decision_records and outcomes length mismatch
    """
    if len(decision_records) != len(outcomes):
        raise ValueError(
            f"Length mismatch: {len(decision_records)} records vs {len(outcomes)} outcomes"
        )

    tracker = CalibrationTracker(agent_name=None)  # System-wide

    for record, was_correct in zip(decision_records, outcomes):
        confidence = record.system_confidence if record.system_confidence else record.confidence
        if confidence is not None:
            tracker.record_outcome(confidence=confidence, was_correct=was_correct)

    return tracker.get_calibration_metrics()


def assess_calibration_health(
    metrics: CalibrationMetrics, threshold: float = 0.1, min_samples: int = 10
) -> str:
    """Assess calibration health status from metrics.

    Returns health status for displaying calibration status in UI.

    Args:
        metrics: CalibrationMetrics to assess
        threshold: ECE threshold for "well_calibrated" status (default 0.1)
        min_samples: Minimum samples for valid assessment (default 10)

    Returns:
        Health status: "well_calibrated", "poorly_calibrated", or "insufficient_data"
    """
    if metrics.sample_count < min_samples:
        return "insufficient_data"
    elif metrics.is_well_calibrated:
        return "well_calibrated"
    else:
        return "poorly_calibrated"


# Confidence history integration helpers


def get_confidence_history(
    store: Optional["SQLiteDecisionStore"] = None, **filters
) -> ConfidenceHistory:
    """Factory function that creates ConfidenceHistory with optional filters.

    Provides a convenient way to create a ConfidenceHistory instance
    with pre-configured filters.

    Args:
        store: Optional SQLite storage backend
        **filters: Optional filter parameters (ticker, agent_type, dates, etc.)

    Returns:
        ConfidenceHistory instance ready for querying
    """
    return ConfidenceHistory(store=store)


def get_confidence_summary(
    ticker: Optional[str] = None,
    agent_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> ConfidenceSummary:
    """Convenience function for quick confidence summary assessment.

    Creates store, history, and returns summary statistics.

    Args:
        ticker: Optional ticker filter
        agent_type: Optional agent type filter
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        ConfidenceSummary with aggregate statistics
    """
    history = get_confidence_history()
    return history.get_confidence_summary(
        ticker=ticker, agent_type=agent_type, start_date=start_date, end_date=end_date
    )


def get_confidence_trend(
    ticker: str,
    agent_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> ConfidenceTrend:
    """Convenience function for trend analysis.

    Returns trend data for specified ticker and date range.

    Args:
        ticker: Ticker symbol to analyze
        agent_type: Optional agent type filter
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)

    Returns:
        ConfidenceTrend with dates, confidences, and slope
    """
    history = get_confidence_history()
    return history.get_confidence_trend(
        ticker=ticker, agent_type=agent_type, start_date=start_date, end_date=end_date
    )


def assess_confidence_reliability(
    ticker: str, threshold: float = 0.8
) -> Dict[str, any]:
    """Assess confidence reliability by combining history and calibration data.

    Provides a comprehensive reliability assessment for informed decision-making.

    Args:
        ticker: Ticker symbol to assess
        threshold: Confidence threshold for "high confidence" classification

    Returns:
        Dict with {
            'high_conf_count': number of high confidence decisions,
            'high_conf_accuracy': accuracy of high confidence decisions,
            'calibration_status': calibration health status,
            'recommendation': trust recommendation (TRUST/CAUTION/DEFER),
            'summary': human-readable summary
        }
    """
    from tradingagents.observability.storage import get_decision_store

    store = get_decision_store()
    history = ConfidenceHistory(store=store)

    # Get high confidence decisions
    high_conf_records = history.get_high_confidence_decisions(
        ticker=ticker, threshold=threshold
    )
    high_conf_count = len(high_conf_records)

    # Get calibration metrics
    calibration = history.get_calibration_summary()

    # Assess calibration health
    cal_health = assess_calibration_health(calibration)

    # Determine recommendation
    if cal_health == "well_calibrated" and high_conf_count >= 10:
        recommendation = "TRUST"
        summary = f"High confidence decisions ({threshold*100:.0f}%+): {high_conf_count}, calibration: well calibrated, recommendation: TRUST"
    elif cal_health == "insufficient_data":
        recommendation = "CAUTION"
        summary = f"Insufficient data for reliable assessment (only {calibration.sample_count} outcomes), recommendation: CAUTION"
    else:
        recommendation = "DEFER"
        summary = f"High confidence decisions ({threshold*100:.0f}%+): {high_conf_count}, calibration: poorly calibrated (ECE={calibration.ece:.3f}), recommendation: DEFER"

    return {
        "high_conf_count": high_conf_count,
        "high_conf_accuracy": None,  # Requires outcome data from Phase 5
        "calibration_status": cal_health,
        "calibration_ece": calibration.ece,
        "calibration_sample_count": calibration.sample_count,
        "recommendation": recommendation,
        "summary": summary,
    }

__all__ = [
    # Models
    "AgentConfidence",
    "ConfidenceMetadata",
    # Scoring
    "ConfidenceScorer",
    "calculate_ensemble_confidence",
    "extract_token_confidence",
    "extract_verbalized_confidence",
    # Aggregation
    "ConfidenceAggregator",
    "weighted_average",
    "bayesian_aggregate",
    "consensus_minimum",
    # Calibration
    "CalibrationTracker",
    "CalibrationMetrics",
    "calculate_ece",
    # History
    "ConfidenceHistory",
    "ConfidenceSummary",
    "ConfidenceTrend",
    "compute_trend_slope",
    "group_by_agent",
    # Integration helpers
    "create_calibration_tracker",
    "compute_system_calibration",
    "assess_calibration_health",
    "get_confidence_history",
    "get_confidence_summary",
    "get_confidence_trend",
    "assess_confidence_reliability",
]
