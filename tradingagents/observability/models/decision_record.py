"""Decision record data model with outcome tracking hooks.

This module defines the DecisionRecord Pydantic model for capturing agent
trading decisions with built-in support for outcome correlation (Phase 5).
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, validator

from tradingagents.backtracking.agent_tracker import TradingSignal


class DebateState(BaseModel):
    """Structured debate state from researcher agents."""

    bull_history: str = Field(default="")
    bear_history: str = Field(default="")
    judge_decision: str = Field(default="")
    history: str = Field(default="")
    current_response: str = Field(default="")
    count: int = Field(default=0)


class DecisionRecord(BaseModel):
    """Record of an agent decision with outcome tracking hooks.

    Extends the existing PredictionRecord pattern from agent_tracker.py
    with additional fields for comprehensive observability.

    Attributes:
        decision_id: Unique identifier for this decision
        ticker: Stock ticker symbol
        trade_date: Trade date in YYYY-MM-DD format
        timestamp: ISO timestamp of when the decision was made
        run_id: Optional identifier for grouping events from a single graph execution
        agent_name: Name of the agent making the decision
        agent_type: Type of agent (analyst, researcher, debater, manager, trader, etc.)
        decision: The trading decision (BUY, SELL, HOLD, or text description)
        reasoning: The agent's reasoning for the decision
        outcome_pending: Whether outcome calculation is pending (DATA-03 requirement)
        entry_price: Entry price for outcome calculation
        exit_price: Exit price for outcome calculation
        hold_days: Number of days to hold for outcome calculation (default 7)
        return_pct: Calculated return percentage (filled during outcome calculation)
        outcome_calculated: Whether the outcome has been calculated
        outcome_calculated_at: Timestamp when outcome was calculated
        confidence: Confidence score (0.0-1.0), placeholder for Phase 2
        bull_signal: Bullish trading signal from debate
        bear_signal: Bearish trading signal from debate
        risk_signal: Risk assessment trading signal
        final_signal: Final trading signal decision
        metadata: Additional metadata as key-value pairs
    """

    # Core context fields
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    ticker: str
    trade_date: str  # YYYY-MM-DD format
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    run_id: Optional[str] = None  # For grouping events from a single graph execution

    # Agent decision fields
    agent_name: str
    agent_type: Literal[
        "analyst",
        "researcher",
        "debater",
        "manager",
        "trader",
        "risk_judge",
        "portfolio_manager",
    ]
    decision: str
    reasoning: str

    # Outcome tracking hooks (DATA-03 requirement)
    outcome_pending: bool = Field(default=True)
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    hold_days: int = Field(default=7)
    return_pct: Optional[float] = None
    outcome_calculated: bool = Field(default=False)
    outcome_calculated_at: Optional[datetime] = None

    # Confidence placeholder (for Phase 2)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # System-level aggregated confidence (CONF-02 requirement)
    system_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="System-level aggregated confidence from all agents (CONF-02)"
    )

    # Individual agent confidences contributing to system_confidence
    agent_confidences: Dict[str, float] = Field(
        default_factory=dict,
        description="Individual agent confidence scores contributing to system_confidence"
    )

    # Debate/analysis capture fields
    bull_signal: Optional[TradingSignal] = None
    bear_signal: Optional[TradingSignal] = None
    risk_signal: Optional[TradingSignal] = None
    final_signal: TradingSignal = TradingSignal.UNKNOWN

    # Structured debate state (for researcher agents)
    debate_state: Optional[DebateState] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

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

    @validator("timestamp")
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is a valid ISO format string."""
        try:
            # Try parsing as ISO format
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
            TradingSignal: lambda v: v.value if isinstance(v, TradingSignal) else v,
        }

        # Allow enum values to be set from strings
        use_enum_values = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the decision record
        """
        data = self.dict(exclude_none=False)
        # Convert TradingSignal enums to their string values
        if self.bull_signal is not None:
            data["bull_signal"] = self.bull_signal.value
        if self.bear_signal is not None:
            data["bear_signal"] = self.bear_signal.value
        if self.risk_signal is not None:
            data["risk_signal"] = self.risk_signal.value
        data["final_signal"] = self.final_signal.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionRecord":
        """Create DecisionRecord from dictionary.

        Args:
            data: Dictionary representation of the decision record

        Returns:
            DecisionRecord instance
        """
        # Convert signal strings back to enums
        signal_fields = ["bull_signal", "bear_signal", "risk_signal", "final_signal"]
        for field in signal_fields:
            if field in data and isinstance(data[field], str):
                data[field] = TradingSignal.from_string(data[field])

        return cls(**data)

    def calculate_outcome(
        self, entry_price: float, exit_price: float
    ) -> Optional[float]:
        """Calculate and update outcome metrics.

        Args:
            entry_price: Price at trade entry
            exit_price: Price at exit

        Returns:
            Return percentage
        """
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.return_pct = ((exit_price - entry_price) / entry_price) * 100
        self.outcome_calculated = True
        self.outcome_calculated_at = datetime.utcnow()
        self.outcome_pending = False

        return self.return_pct
