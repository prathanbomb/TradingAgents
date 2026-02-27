"""Decision trail data models for timeline and causal chain visualization.

This module defines Pydantic models for organizing captured events and records
into decision trails that show both chronological timeline and causal relationships.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class TrailNode(BaseModel):
    """A single decision point in the decision trail.

    Represents an agent decision at a specific point in time, extracted from
    DecisionRecord for display in the trail timeline.

    Attributes:
        node_id: Unique identifier for this node
        timestamp: ISO timestamp of when the decision occurred
        agent_name: Name of the agent that made this decision
        agent_type: Type of agent (analyst, researcher, manager, trader, etc.)
        decision: The trading decision or action taken
        confidence: Optional confidence score (0.0-1.0 range)
        reasoning: Truncated reasoning text (200 chars for display)
        node_type: Distinguishes between decision nodes and event nodes
    """

    node_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    agent_name: str
    agent_type: Literal[
        "analyst",
        "researcher",
        "manager",
        "trader",
        "risk_judge",
        "portfolio_manager",
    ]
    decision: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reasoning: str = Field(default="")
    node_type: Literal["decision", "event"] = Field(default="decision")

    @validator("timestamp")
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is a valid ISO format string."""
        try:
            if isinstance(v, str):
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError as e:
            raise ValueError(
                f"timestamp must be a valid ISO format string, got: {v}"
            ) from e

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the trail node
        """
        return self.dict(exclude_none=True)


class TrailEdge(BaseModel):
    """A causal link between decision points in the trail.

    Represents a causal connection from one agent/node to another, extracted
    from AgentEvent state_transition events to show the decision flow.

    Attributes:
        edge_id: Unique identifier for this edge
        source: The agent/node that initiated the action (from_state)
        target: The agent/node that received the action (to_state)
        timestamp: ISO timestamp of when the transition occurred
        agent_name: Which agent caused this transition
        edge_type: Distinguishes LangGraph edges from causal influences
    """

    edge_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    target: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    agent_name: str
    edge_type: Literal["state_transition", "output_influences"] = Field(
        default="state_transition"
    )

    @validator("timestamp")
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is a valid ISO format string."""
        try:
            if isinstance(v, str):
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError as e:
            raise ValueError(
                f"timestamp must be a valid ISO format string, got: {v}"
            ) from e

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the trail edge
        """
        return self.dict(exclude_none=True)


class DecisionTrail(BaseModel):
    """Container for a complete decision trail.

    Groups all decision points and causal links from a single graph execution,
    organized by run_id to show the complete decision flow from data input
    through analysis to final recommendation.

    Attributes:
        trail_id: Unique identifier for this trail
        run_id: Groups events from single graph execution
        ticker: Stock ticker symbol
        trade_date: Trade date in YYYY-MM-DD format
        nodes: All decision points in chronological order
        edges: All causal links between decisions
        started_at: ISO timestamp of first event
        completed_at: ISO timestamp of final decision
    """

    trail_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    ticker: str
    trade_date: str  # YYYY-MM-DD format
    nodes: List[TrailNode] = Field(default_factory=list)
    edges: List[TrailEdge] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @validator("trade_date")
    def validate_trade_date(cls, v: str) -> str:
        """Validate trade_date is in YYYY-MM-DD format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError as e:
            raise ValueError(
                f"trade_date must be in YYYY-MM-DD format, got: {v}"
            ) from e

    @validator("started_at", "completed_at")
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is a valid ISO format string."""
        try:
            if isinstance(v, str):
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError as e:
            raise ValueError(
                f"timestamp must be a valid ISO format string, got: {v}"
            ) from e

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def get_agent_nodes(self, agent_name: str) -> List[TrailNode]:
        """Filter nodes by agent name.

        Args:
            agent_name: Name of the agent to filter by

        Returns:
            List of nodes for the specified agent
        """
        return [node for node in self.nodes if node.agent_name == agent_name]

    def get_outgoing_edges(self, source: str) -> List[TrailEdge]:
        """Find edges originating from a specific source node.

        Args:
            source: Source node identifier

        Returns:
            List of edges from the specified source
        """
        return [edge for edge in self.edges if edge.source == source]

    def get_duration_seconds(self) -> float:
        """Calculate the duration from start to completion.

        Returns:
            Duration in seconds as a float
        """
        try:
            start = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(self.completed_at.replace("Z", "+00:00"))
            return (end - start).total_seconds()
        except (ValueError, AttributeError):
            return 0.0

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the decision trail
        """
        return self.dict(exclude_none=True)
