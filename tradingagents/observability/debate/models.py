"""Debate data models for structured argument extraction.

This module defines Pydantic models for representing structured debate data
extracted from DecisionRecord.debate_state, including individual arguments,
judgments, and complete debate containers.
"""

import logging
from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class Argument(BaseModel):
    """A single argument from a debate participant.

    Represents one turn in a debate, extracted from unstructured conversation
    history using speaker prefix patterns.

    Attributes:
        argument_id: Unique identifier for this argument
        speaker: Speaker name (e.g., "Bull Analyst", "Risky Analyst")
        content: Full text of the argument
        turn_number: Position in debate sequence (1-indexed)
        argument_type: Optional classification (e.g., "data_driven", "qualitative")
        timestamp: Optional timestamp when argument was made
    """

    argument_id: str = Field(default_factory=lambda: str(uuid4()))
    speaker: str
    content: str
    turn_number: int = Field(ge=1)
    argument_type: Optional[Literal["data_driven", "qualitative"]] = None
    timestamp: Optional[str] = None

    @validator("timestamp")
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """Validate timestamp is a valid ISO format string."""
        if v is None:
            return v
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
            Dictionary representation of the argument
        """
        return self.dict(exclude_none=True)


class Judgment(BaseModel):
    """The judge's resolution of a debate.

    Represents the final decision made by the judge after hearing all arguments.

    Attributes:
        judgment_id: Unique identifier for this judgment
        decision: The judge's decision text (e.g., "Bull case is stronger")
        judge: Name of the judge (e.g., "Investment Judge", "Risk Judge")
        reasoning: Optional explanation for the decision
        timestamp: Optional timestamp of judgment
    """

    judgment_id: str = Field(default_factory=lambda: str(uuid4()))
    decision: str
    judge: str
    reasoning: Optional[str] = None
    timestamp: Optional[str] = None

    @validator("timestamp")
    def validate_timestamp(cls, v: Optional[str]) -> Optional[str]:
        """Validate timestamp is a valid ISO format string."""
        if v is None:
            return v
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
            Dictionary representation of the judgment
        """
        return self.dict(exclude_none=True)


class Debate(BaseModel):
    """A complete debate with all arguments and judgment.

    Container for structured debate data extracted from DecisionRecord.debate_state,
    including all arguments in chronological order and the final judgment.

    Attributes:
        debate_id: Unique identifier for this debate
        debate_type: Type of debate ("investment" or "risk")
        run_id: Links to DecisionRecord and DecisionTrail
        ticker: Stock ticker symbol
        trade_date: Trade date in YYYY-MM-DD format
        arguments: List of all arguments in chronological order
        judgment: The judge's final decision
        total_turns: Total number of argument turns
        started_at: ISO timestamp of first argument
        completed_at: ISO timestamp of judgment
    """

    debate_id: str = Field(default_factory=lambda: str(uuid4()))
    debate_type: Literal["investment", "risk"]
    run_id: str
    ticker: str
    trade_date: str  # YYYY-MM-DD format
    arguments: List[Argument] = Field(default_factory=list)
    judgment: Optional[Judgment] = None
    total_turns: int = Field(default=0, ge=0)
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

    @validator("total_turns")
    def validate_total_turns(cls, v: int, values: Dict) -> int:
        """Validate total_turns matches arguments list length."""
        if "arguments" in values and len(values["arguments"]) != v:
            # If mismatch, update total_turns to match actual arguments
            return len(values["arguments"])
        return v

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def get_speaker_arguments(self, speaker: str) -> List[Argument]:
        """Filter arguments by speaker name.

        Args:
            speaker: Name of the speaker to filter by

        Returns:
            List of arguments from the specified speaker
        """
        return [arg for arg in self.arguments if arg.speaker == speaker]

    def get_argument_types(self) -> Dict[str, int]:
        """Count arguments by type.

        Returns:
            Dictionary mapping argument_type to count
        """
        type_counts: Dict[str, int] = {}
        for arg in self.arguments:
            arg_type = arg.argument_type or "unknown"
            type_counts[arg_type] = type_counts.get(arg_type, 0) + 1
        return type_counts

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the debate
        """
        return self.dict(exclude_none=True)


class DebateSummary(BaseModel):
    """Progressive disclosure model for debate display.

    Provides 3 levels of detail to avoid overwhelming users:
    1. Summary (always shown) - 1-2 sentence overview
    2. Key points (expandable) - 3-5 bullet points per speaker
    3. Full transcript (expandable) - complete argument text

    Attributes:
        summary_id: Unique identifier for this summary
        debate_id: Links to parent Debate
        debate_type: Type of debate ("investment" or "risk")

        # Level 1: Summary (always shown)
        summary: str  # 1-2 sentence overview
        judgment_summary: str  # How judge resolved the debate
        total_turns: int  # Debate length context
        total_arguments: int  # Number of arguments

        # Level 2: Key points (expandable)
        bull_key_points: Optional[List[str]] = None
        bear_key_points: Optional[List[str]] = None
        risky_key_points: Optional[List[str]] = None
        safe_key_points: Optional[List[str]] = None
        neutral_key_points: Optional[List[str]] = None

        # Level 3: Full transcript (expandable)
        full_transcript: Optional[str] = None

        # Metadata
        created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
        llm_model: Optional[str] = None  # Which model generated summary
    """

    summary_id: str = Field(default_factory=lambda: str(uuid4()))
    debate_id: str
    debate_type: Literal["investment", "risk"]

    # Level 1: Summary (always shown)
    summary: str
    judgment_summary: str
    total_turns: int
    total_arguments: int

    # Level 2: Key points (expandable)
    bull_key_points: Optional[List[str]] = None
    bear_key_points: Optional[List[str]] = None
    risky_key_points: Optional[List[str]] = None
    safe_key_points: Optional[List[str]] = None
    neutral_key_points: Optional[List[str]] = None

    # Level 3: Full transcript (expandable)
    full_transcript: Optional[str] = None

    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    llm_model: Optional[str] = None

    @validator("summary")
    def validate_summary_length(cls, v: str) -> str:
        """Validate and truncate summary to max length.

        Args:
            v: Summary string

        Returns:
            Truncated summary if exceeds max length
        """
        max_length = 280
        if len(v) > max_length:
            logger = __import__("logging").getLogger(__name__)
            logger.warning(f"Summary exceeds {max_length} chars, truncating")
            return v[:max_length - 3] + "..."
        return v

    def get_key_points_for_speaker(self, speaker: str) -> Optional[List[str]]:
        """Get key points for a specific speaker.

        Args:
            speaker: Speaker name (e.g., "Bull Analyst", "Risky Analyst")

        Returns:
            List of key points for the speaker, or None if not found
        """
        speaker_to_field = {
            "Bull Analyst": "bull_key_points",
            "Bear Analyst": "bear_key_points",
            "Risky Analyst": "risky_key_points",
            "Safe Analyst": "safe_key_points",
            "Neutral Analyst": "neutral_key_points",
        }
        field = speaker_to_field.get(speaker)
        if field:
            return getattr(self, field)
        return None

    def to_dict(self, exclude_level: int = 0) -> Dict[str, any]:
        """Convert to dictionary for progressive disclosure.

        Args:
            exclude_level: Level of detail to exclude (0=full, 2=exclude transcript)

        Returns:
            Dictionary representation with optional exclusions
        """
        exclude = {"full_transcript"} if exclude_level >= 3 else set()
        return self.dict(exclude=exclude if exclude else None, exclude_none=True)

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

        json_schema_extra = {
            "example": {
                "summary_id": "123e4567-e89b-12d3-a456-426614174000",
                "debate_id": "debate-123",
                "debate_type": "investment",
                "summary": "Bull argues strong earnings growth while Bear highlights valuation concerns. Judge favors Bull due to momentum.",
                "judgment_summary": "Bull case is stronger based on recent earnings momentum.",
                "total_turns": 6,
                "total_arguments": 6,
                "bull_key_points": [
                    "EPS grew 25% YoY, beating estimates",
                    "Revenue guidance raised for Q3",
                    "Technical indicators show breakout",
                ],
                "bear_key_points": [
                    "P/E ratio 40% above sector average",
                    "Margin pressure from input costs",
                    "Competitive landscape intensifying",
                ],
                "full_transcript": "Turn 1 - Bull Analyst: ...",
                "created_at": "2024-01-15T10:30:00Z",
                "llm_model": "gpt-3.5-turbo",
            }
        }


class JudgmentView(BaseModel):
    """Structured view of debate resolution for display.

    Provides progressive disclosure from summary to full judgment details.

    Attributes:
        view_id: Unique identifier for this view
        debate_id: Links to parent Debate

        # Level 1: Summary (always shown)
        winner: str  # Which speaker/side won (e.g., "Bull Analyst", "Safe Analyst")
        winner_summary: str  # 1-sentence summary of why they won
        judgment_summary: str  # Truncated judgment text (200 chars)

        # Level 2: Key arguments (expandable)
        winning_arguments: Optional[List[str]] = None  # Key arguments from winner
        losing_arguments: Optional[List[str]] = None  # Key arguments from loser
        judgment_reasoning: Optional[str] = None  # Extracted reasoning

        # Level 3: Full details (expandable)
        full_judgment: Optional[str] = None  # Complete judgment text
        all_arguments: Optional[Dict[str, List[str]]] = None  # All arguments by speaker

        # Metadata
        confidence: Optional[float] = None  # Judge's confidence in decision (if available)
        timestamp: Optional[str] = None  # When judgment was made
    """

    view_id: str = Field(default_factory=lambda: str(uuid4()))
    debate_id: str

    # Level 1: Summary (always shown)
    winner: str = Field(description="Which speaker/side won the debate")
    winner_summary: str = Field(description="1-sentence summary of why they won")
    judgment_summary: str = Field(description="Truncated judgment text (200 chars)")

    # Level 2: Key arguments (expandable)
    winning_arguments: Optional[List[str]] = Field(default=None, description="Key arguments from winner")
    losing_arguments: Optional[List[str]] = Field(default=None, description="Key arguments from loser")
    judgment_reasoning: Optional[str] = Field(default=None, description="Extracted reasoning")

    # Level 3: Full details (expandable)
    full_judgment: Optional[str] = Field(default=None, description="Complete judgment text")
    all_arguments: Optional[Dict[str, List[str]]] = Field(default=None, description="All arguments by speaker")

    # Metadata
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Judge's confidence in decision")
    timestamp: Optional[str] = Field(default=None, description="When judgment was made")

    @validator("winner_summary")
    def validate_winner_summary_length(cls, v: str) -> str:
        """Validate and truncate winner_summary to max length."""
        max_length = 200
        if len(v) > max_length:
            logger.warning(f"winner_summary exceeds {max_length} chars, truncating")
            return v[:max_length - 3] + "..."
        return v

    @validator("judgment_summary")
    def validate_judgment_summary_length(cls, v: str) -> str:
        """Validate and truncate judgment_summary to max length."""
        max_length = 200
        if len(v) > max_length:
            logger.warning(f"judgment_summary exceeds {max_length} chars, truncating")
            return v[:max_length - 3] + "..."
        return v

    def to_dict(self, exclude_level: int = 0) -> Dict[str, any]:
        """Convert to dictionary for progressive disclosure.

        Args:
            exclude_level: Level of detail to exclude (0=full, 2=exclude level 2+, 3=exclude level 3)

        Returns:
            Dictionary representation with optional exclusions
        """
        exclude = set()
        if exclude_level >= 2:
            exclude.update({"winning_arguments", "losing_arguments", "judgment_reasoning"})
        if exclude_level >= 3:
            exclude.update({"full_judgment", "all_arguments"})
        return self.dict(exclude=exclude if exclude else None, exclude_none=True)


class DecisionInfluence(BaseModel):
    """Analysis of how debate influenced final trading decision.

    Links debate judgment to DecisionRecord.final_signal to measure alignment.

    Attributes:
        influence_id: Unique identifier
        debate_id: Links to Debate
        decision_id: Links to DecisionRecord

        judgment_winner: Which side won the debate (bull/bear/risky/safe/neutral)
        final_decision: Final trading signal (BUY/SELL/HOLD)
        alignment: Literal["aligned", "opposed", "neutral"]  # Did judgment match decision?
        influence_score: float  # 0.0-1.0 score of how much debate influenced decision

        reasoning: str  # Explanation of alignment (e.g., "Bull won, decision is BUY")
    """

    influence_id: str = Field(default_factory=lambda: str(uuid4()))
    debate_id: str = Field(description="Links to Debate")
    decision_id: str = Field(description="Links to DecisionRecord")

    judgment_winner: str = Field(description="Which side won the debate")
    final_decision: str = Field(description="Final trading signal (BUY/SELL/HOLD)")
    alignment: Literal["aligned", "opposed", "neutral"] = Field(description="Did judgment match decision?")
    influence_score: float = Field(ge=0.0, le=1.0, description="0.0-1.0 score of how much debate influenced decision")

    reasoning: str = Field(description="Explanation of alignment")

    def get_alignment_description(self) -> str:
        """Get human-readable description of alignment.

        Returns:
            Human-readable alignment description
        """
        if self.alignment == "aligned":
            return f"Judgment ({self.judgment_winner}) aligns with decision ({self.final_decision})"
        elif self.alignment == "opposed":
            return f"Judgment ({self.judgment_winner}) opposes decision ({self.final_decision})"
        else:
            return f"Judgment ({self.judgment_winner}) is neutral to decision ({self.final_decision})"
