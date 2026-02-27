"""Observability instrumentation for LangGraph event collection.

This module provides non-invasive instrumentation for capturing
agent decisions and execution events via LangGraph streaming.

Integration Pattern:
    ```python
    from tradingagents.observability.instrumentation import create_observation_run

    # Before propagate(): Create collector and extractor
    run_id, collector, extractor = create_observation_run(ticker="AAPL")

    # During propagate(): Stream events via collector.collect_events()
    async for event in collector.collect_events(graph, input_state):
        # Events captured in real-time
        pass

    # After propagate(): Extract decisions via extractor.extract_decision_records()
    decision_records = extractor.extract_decision_records(final_state, ticker, trade_date, run_id)

    # Pass both to async storage pipeline (Plan 03)
    ```
"""

import logging
import uuid
from typing import Tuple

from .langgraph_collector import LanggraphCollector
from .state_extractor import StateExtractor

# Configure module-level logging
logger = logging.getLogger(__name__)

__all__ = [
    "LanggraphCollector",
    "StateExtractor",
    "create_observation_run",
]


def create_observation_run(ticker: str = None) -> Tuple[str, LanggraphCollector, StateExtractor]:
    """Create a new observation run with linked components.

    This convenience function creates a collector and extractor with a shared run_id,
    making it easy to track events and decisions from a single graph execution.

    Args:
        ticker: Optional stock ticker for this observation run

    Returns:
        Tuple of (run_id, collector, extractor) with matching run_id

    Example:
        ```python
        run_id, collector, extractor = create_observation_run("AAPL")

        # Use collector during graph execution
        async for event in collector.collect_events(graph, state):
            logger.info(f"Event: {event.event_type}")

        # Use extractor after graph execution
        records = extractor.extract_decision_records(final_state, "AAPL", "2026-02-27", run_id)
        ```
    """
    run_id = str(uuid.uuid4())
    collector = LanggraphCollector(run_id=run_id)
    extractor = StateExtractor()

    logger.debug(f"Created observation run {run_id} for ticker={ticker or 'unknown'}")

    return run_id, collector, extractor


def get_instrumentation_config() -> dict:
    """Get default configuration for observability instrumentation.

    Returns:
        Dict with default configuration values for event collection and state extraction
    """
    return {
        "event_filtering": {
            "capture_llm_calls": True,
            "capture_tool_usage": True,
            "capture_state_transitions": True,
            "sample_full_transcripts": 0.1,  # 10% sampling rate
        },
        "state_extraction": {
            "truncate_reports": 1000,  # Max characters for report reasoning
            "extract_debate_history": True,
            "extract_analyst_reports": True,
        },
        "performance": {
            "async_timeout": 1.0,  # Seconds to wait for queue
            "max_event_buffer": 1000,  # Max events to buffer
        },
    }

