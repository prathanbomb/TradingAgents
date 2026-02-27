"""Confidence data models for agent decision confidence scoring.

This module defines Pydantic models for confidence data with validation,
following the pattern from DecisionRecord.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentConfidence(BaseModel):
    """Confidence score with method tracking and metadata.

    Represents a confidence score extracted from an agent's output,
    including the method used for extraction and additional context.

    Attributes:
        score: Confidence score between 0.0 and 1.0
        method: Method used to calculate confidence (verbalized, ensemble,
            token_probability, fallback)
        metadata: Additional context (sample_count, patterns_found, etc.)
    """

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )
    method: str = Field(
        description="Method used to calculate confidence"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about confidence calculation"
    )


class ConfidenceMetadata(BaseModel):
    """Detailed metadata for confidence calculation results.

    Provides structured metadata for confidence scores, including
    information about ensemble samples, verbalized patterns, and
    token probability statistics.

    Attributes:
        ensemble_samples: Number of samples used for ensemble confidence
        verbalized_patterns: Patterns matched in text for verbalized confidence
        token_probability_avg: Average token probability for token-based confidence
        fallback_reason: Reason why fallback was used (if applicable)
    """

    ensemble_samples: Optional[int] = Field(
        default=None,
        description="Number of samples used for ensemble confidence"
    )
    verbalized_patterns: List[str] = Field(
        default_factory=list,
        description="Patterns matched in text for verbalized confidence"
    )
    token_probability_avg: Optional[float] = Field(
        default=None,
        description="Average token probability for token-based confidence"
    )
    fallback_reason: Optional[str] = Field(
        default=None,
        description="Reason why fallback was used"
    )
