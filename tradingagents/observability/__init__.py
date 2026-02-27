"""Trading Agents Observatory - Data Collection & Instrumentation.

This module provides comprehensive observability for the multi-agent trading system,
including decision tracking, event capture, and outcome correlation.

Phase 1 (Data Collection): Pydantic models for decision records and agent events
Phase 2 (Confidence Scoring): Confidence extraction and calibration
Phase 3 (Decision Trail): Query interface and visualization
Phase 4 (Performance Correlation): Outcome tracking and analysis
Phase 5 (API Layer): REST API for observability data

Example usage:
    ```python
    from tradingagents.observability import DecisionRecord, AgentEvent

    # Create a decision record
    record = DecisionRecord(
        ticker="AAPL",
        trade_date="2026-02-27",
        agent_name="bull_researcher",
        agent_type="researcher",
        decision="BUY",
        reasoning="Strong fundamentals and positive sentiment"
    )

    # Create an agent event
    event = AgentEvent.create_llm_call(
        agent_name="bull_researcher",
        model="gpt-4o",
        total_tokens=1250
    )
    ```
"""

from tradingagents.observability.models import (
    AgentEvent,
    DecisionRecord,
)

__all__ = [
    "AgentEvent",
    "DecisionRecord",
]

# Version marker for future compatibility
__version__ = "0.1.0"  # Phase 1: Data Collection & Instrumentation

# Configure logging for the observability module
import logging

logger = logging.getLogger(__name__)
