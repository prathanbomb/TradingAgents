"""Confidence aggregation for multi-agent decision fusion.

This module provides ConfidenceAggregator for combining individual agent
confidence scores into system-level confidence using multiple methods:
weighted average, Bayesian aggregation, and minimum consensus.
"""

import logging
from typing import Dict, Literal, Optional

import numpy as np

logger = logging.getLogger(__name__)


def weighted_average(
    confidences: Dict[str, float], weights: Dict[str, float]
) -> float:
    """Aggregate confidences using accuracy-based weighted average.

    Args:
        confidences: Dictionary mapping agent names to confidence scores
        weights: Dictionary mapping agent names to accuracy weights

    Returns:
        Weighted average confidence score between 0-1

    Raises:
        ValueError: If weights empty, agent names mismatch, or invalid values
    """
    if not confidences:
        logger.warning("Empty confidences dict, returning neutral 0.5")
        return 0.5

    if not weights:
        raise ValueError("Weights dictionary cannot be empty for weighted aggregation")

    # Validate agent names match
    confidence_agents = set(confidences.keys())
    weight_agents = set(weights.keys())

    if confidence_agents != weight_agents:
        raise ValueError(
            f"Agent names mismatch: confidences has {confidence_agents}, "
            f"weights has {weight_agents}"
        )

    # Validate ranges
    for agent, conf in confidences.items():
        if not 0.0 <= conf <= 1.0:
            raise ValueError(f"Confidence for {agent}={conf} not in [0, 1] range")

    for agent, weight in weights.items():
        if weight < 0:
            raise ValueError(f"Weight for {agent}={weight} is negative")

    # Compute weighted average
    total_weight = sum(weights.values())
    if total_weight == 0:
        raise ValueError("Total weight cannot be zero")

    weighted_sum = sum(conf * weights[agent] for agent, conf in confidences.items())
    result = weighted_sum / total_weight

    # Clamp to valid range (should already be in range, but ensure)
    result = max(0.0, min(1.0, result))

    logger.debug(
        f"Weighted aggregation: {result:.3f} from {len(confidences)} agents "
        f"(total_weight={total_weight:.2f})"
    )

    return result


def bayesian_aggregate(
    confidences: Dict[str, float],
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> float:
    """Aggregate confidences using Bayesian updating with Beta prior.

    Treats each confidence as evidence for a Beta distribution, computing
    the posterior expected value. This is equivalent to treating confidences
    as probabilities and combining them using Bayesian inference.

    Args:
        confidences: Dictionary mapping agent names to confidence scores
        prior_alpha: Alpha parameter for Beta prior (default: 1.0 for uniform)
        prior_beta: Beta parameter for Beta prior (default: 1.0 for uniform)

    Returns:
        Expected value of posterior Beta distribution between 0-1
    """
    if not confidences:
        logger.debug("Empty confidences dict, returning uniform prior 0.5")
        return 0.5

    # Validate ranges
    for agent, conf in confidences.items():
        if not 0.0 <= conf <= 1.0:
            raise ValueError(f"Confidence for {agent}={conf} not in [0, 1] range")

    # Compute posterior parameters
    # Each confidence adds evidence: alpha += confidence, beta += (1 - confidence)
    posterior_alpha = prior_alpha + sum(confidences.values())
    posterior_beta = prior_beta + sum(1.0 - conf for conf in confidences.values())

    # Expected value of Beta distribution
    result = posterior_alpha / (posterior_alpha + posterior_beta)

    logger.debug(
        f"Bayesian aggregation: {result:.3f} (alpha={posterior_alpha:.2f}, "
        f"beta={posterior_beta:.2f}) from {len(confidences)} agents"
    )

    return result


def consensus_minimum(confidences: Dict[str, float]) -> float:
    """Aggregate using minimum consensus (weakest link approach).

    Returns the minimum confidence across all agents, providing a
    conservative aggregation suitable for high-stakes decisions.

    Args:
        confidences: Dictionary mapping agent names to confidence scores

    Returns:
        Minimum confidence score, or 0.5 if confidences empty
    """
    if not confidences:
        logger.debug("Empty confidences dict, returning neutral 0.5")
        return 0.5

    # Validate ranges
    for agent, conf in confidences.items():
        if not 0.0 <= conf <= 1.0:
            raise ValueError(f"Confidence for {agent}={conf} not in [0, 1] range")

    result = min(confidences.values())

    logger.debug(
        f"Consensus aggregation: {result:.3f} (minimum of {len(confidences)} agents)"
    )

    return result


class ConfidenceAggregator:
    """Aggregates multiple agent confidence scores into system-level confidence.

    Supports three fusion methods:
    - weighted: Weighted average by accuracy (requires weights)
    - bayesian: Bayesian aggregation with Beta prior (default)
    - consensus: Minimum confidence (conservative)

    Example:
        ```python
        aggregator = ConfidenceAggregator(method='bayesian')
        confidences = {'analyst': 0.8, 'researcher': 0.7, 'trader': 0.85}
        system_confidence = aggregator.aggregate(confidences)
        # Returns: 0.78 (Bayesian expected value)
        ```
    """

    # Default agent weights based on hierarchy
    DEFAULT_AGENT_WEIGHTS: Dict[str, float] = {
        "market_analyst": 0.15,
        "social_media_analyst": 0.15,
        "news_researcher": 0.15,
        "fundamentals_researcher": 0.15,
        "bull_researcher": 0.20,
        "bear_researcher": 0.20,
        "investment_judge": 0.25,
        "trader": 0.20,
        "risk_judge": 0.20,
        "portfolio_manager": 0.25,
    }

    def __init__(
        self,
        method: Literal["weighted", "bayesian", "consensus"] = "bayesian",
        weights: Optional[Dict[str, float]] = None,
    ):
        """Initialize the confidence aggregator.

        Args:
            method: Aggregation method to use (default: 'bayesian')
            weights: Optional weights for weighted aggregation.
                If method='weighted' and not provided, uses DEFAULT_AGENT_WEIGHTS.
        """
        if method not in ("weighted", "bayesian", "consensus"):
            raise ValueError(
                f"Invalid method: {method}. Must be 'weighted', 'bayesian', or 'consensus'"
            )

        self.method = method
        self.weights = weights or self.get_agent_weights()

        logger.debug(
            f"Initialized ConfidenceAggregator with method='{method}', "
            f"weights={'custom' if weights else 'default'}"
        )

    def get_agent_weights(self) -> Dict[str, float]:
        """Get default agent weights based on hierarchy.

        Returns:
            Dictionary mapping agent names to accuracy weights
        """
        return self.DEFAULT_AGENT_WEIGHTS.copy()

    def aggregate(self, confidences: Dict[str, float]) -> float:
        """Aggregate multiple agent confidences into system-level score.

        Routes to the selected aggregation method.

        Args:
            confidences: Dictionary mapping agent names to confidence scores

        Returns:
            Aggregated system confidence between 0-1

        Raises:
            ValueError: If method is invalid or inputs are invalid
        """
        if not confidences:
            logger.debug("No confidences to aggregate, returning neutral 0.5")
            return 0.5

        if self.method == "weighted":
            return weighted_average(confidences, self._filter_weights(confidences))
        elif self.method == "bayesian":
            return bayesian_aggregate(confidences)
        elif self.method == "consensus":
            return consensus_minimum(confidences)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _filter_weights(self, confidences: Dict[str, float]) -> Dict[str, float]:
        """Filter weights to match agents in confidences dict.

        Args:
            confidences: Dictionary mapping agent names to confidence scores

        Returns:
            Filtered weights dictionary matching confidences keys
        """
        return {
            agent: self.weights.get(agent, 1.0 / len(confidences))
            for agent in confidences.keys()
        }

    def _validate_inputs(
        self, confidences: Dict[str, float], weights: Optional[Dict[str, float]] = None
    ) -> None:
        """Validate input dictionaries.

        Args:
            confidences: Dictionary mapping agent names to confidence scores
            weights: Optional weights dictionary

        Raises:
            ValueError: If inputs are invalid
        """
        if not confidences:
            raise ValueError("Confidences dictionary cannot be empty")

        if not isinstance(confidences, dict):
            raise ValueError("Confidences must be a dictionary")

        # Validate confidence values
        for agent, conf in confidences.items():
            if not isinstance(conf, (int, float)):
                raise ValueError(f"Confidence for {agent} must be numeric")
            if not 0.0 <= conf <= 1.0:
                raise ValueError(f"Confidence for {agent}={conf} not in [0, 1] range")

        # Validate weights if provided
        if weights is not None:
            if not isinstance(weights, dict):
                raise ValueError("Weights must be a dictionary")
            for agent, weight in weights.items():
                if not isinstance(weight, (int, float)):
                    raise ValueError(f"Weight for {agent} must be numeric")
                if weight < 0:
                    raise ValueError(f"Weight for {agent}={weight} is negative")
