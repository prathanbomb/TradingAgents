"""Observability data models for agent decision tracking.

This module defines Pydantic models for capturing agent events and decisions.
"""

from typing import List

from tradingagents.backtracking.agent_tracker import TradingSignal

from .agent_event import AgentEvent
from .decision_record import DecisionRecord, DebateState

# Type aliases for common model collections
DecisionRecords = List[DecisionRecord]
AgentEvents = List[AgentEvent]

__all__ = [
    "AgentEvent",
    "DecisionRecord",
    "DebateState",
    "TradingSignal",
    "DecisionRecords",
    "AgentEvents",
]
