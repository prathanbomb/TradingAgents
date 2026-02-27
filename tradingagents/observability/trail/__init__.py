"""Decision trail data models and builder for timeline visualization.

This module provides Pydantic models for organizing captured events and records
into decision trails that show both chronological timeline and causal relationships
between agent decisions, along with TrailBuilder for constructing trails from
stored events.

The trail models build on Phase 1's DecisionRecord and AgentEvent models to
provide a comprehensive view of decision flow from data input through analysis
to final recommendation.

Example:
    >>> from tradingagents.observability.trail import DecisionTrail, TrailNode, TrailEdge, TrailBuilder, TrailQuery
    >>> from tradingagents.observability.storage.sqlite_backend import SQLiteDecisionStore
    >>> store = SQLiteDecisionStore("./data/observability.db")
    >>> builder = TrailBuilder(store)
    >>> trail = builder.build_trail(run_id="abc123")
    >>> print(f"Trail has {len(trail.nodes)} decisions")
"""

from tradingagents.observability.trail.builder import TrailBuilder
from tradingagents.observability.trail.display import TrailRenderer
from tradingagents.observability.trail.models import DecisionTrail, TrailEdge, TrailNode

__all__ = ["DecisionTrail", "TrailNode", "TrailEdge", "TrailBuilder", "TrailQuery", "TrailRenderer"]

# Lazy import for TrailQuery to avoid circular dependencies
def __getattr__(name: str):
    if name == "TrailQuery":
        from tradingagents.observability.trail.queries import TrailQuery

        return TrailQuery
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
