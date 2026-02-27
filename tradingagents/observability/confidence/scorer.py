"""Confidence scorer for extracting confidence from agent outputs.

This module provides ConfidenceScorer for estimating confidence from LLM
agent outputs using multiple methods: verbalized parsing, ensemble consistency,
and token probability analysis.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

import numpy as np

from tradingagents.observability.confidence.models import AgentConfidence

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Extracts confidence scores from agent outputs using multiple methods.

    Tries estimation methods in order: verbalized (fastest) -> token_probability
    (if available) -> ensemble (if llm provided). Falls back to 0.5 if all fail.

    Example:
        ```python
        scorer = ConfidenceScorer()
        confidence = scorer.score("I am 85% confident this is correct")
        # Returns: AgentConfidence(score=0.85, method='verbalized', ...)
        ```
    """

    # Regex patterns for verbalized confidence
    VERBALIZED_PATTERNS = [
        r"(\d+)%\s*sure",
        r"(\d+)%\s*confident",
        r"confidence[:\s]+(\d+)%",
        r"(\d+)%\s*certain",
        r"probability[:\s]+(\d+)%",
    ]

    def __init__(self):
        """Initialize the confidence scorer."""
        self._sentence_transformer_available = self._check_sentence_transformer()
        logger.debug(f"Initialized ConfidenceScorer (sentence-transformers: {self._sentence_transformer_available})")

    def _check_sentence_transformer(self) -> bool:
        """Check if sentence-transformers is available."""
        try:
            import sentence_transformers  # noqa: F401
            return True
        except ImportError:
            logger.warning(
                "sentence-transformers not available. "
                "Ensemble confidence scoring will be disabled. "
                "Install with: pip install sentence-transformers"
            )
            return False

    def score(
        self,
        agent_output: str,
        llm_output: Optional[Any] = None,
        llm: Optional[Any] = None,
        prompt: Optional[str] = None,
    ) -> AgentConfidence:
        """Extract confidence score from agent output using available methods.

        Tries methods in order: verbalized -> token_probability -> ensemble -> fallback.

        Args:
            agent_output: Text output from the agent
            llm_output: Optional LLM output with logprobs (LangChain format)
            llm: Optional LLM for ensemble sampling (if verbalized fails)
            prompt: Optional prompt for ensemble sampling

        Returns:
            AgentConfidence with score, method, and metadata
        """
        # Try verbalized confidence first (fastest)
        verbalized_score = extract_verbalized_confidence(agent_output)
        if verbalized_score is not None:
            return AgentConfidence(
                score=verbalized_score,
                method="verbalized",
                metadata={"patterns_matched": True}
            )

        # Try token probability if available
        if llm_output is not None:
            token_score = extract_token_confidence(llm_output)
            if token_score is not None:
                return AgentConfidence(
                    score=token_score,
                    method="token_probability",
                    metadata={"logprobs_available": True}
                )

        # Try ensemble if LLM provided (expensive)
        if llm is not None and prompt is not None:
            ensemble_score = self._calculate_ensemble_confidence_sync(llm, prompt)
            if ensemble_score is not None:
                return AgentConfidence(
                    score=ensemble_score,
                    method="ensemble",
                    metadata={"sample_count": 3}
                )

        # Fallback to neutral confidence
        logger.debug("All confidence methods failed, using fallback 0.5")
        return AgentConfidence(
            score=0.5,
            method="fallback",
            metadata={"reason": "no_confidence_extracted"}
        )

    def _calculate_ensemble_confidence_sync(
        self, llm: Any, prompt: str, num_samples: int = 3
    ) -> Optional[float]:
        """Calculate ensemble confidence synchronously (wrapper for async).

        Args:
            llm: LLM instance for sampling
            prompt: Prompt to sample
            num_samples: Number of samples to generate

        Returns:
            Confidence score or None if unavailable
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If running in async context, create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        calculate_ensemble_confidence(llm, prompt, num_samples)
                    )
                    return future.result(timeout=30)
            else:
                # Run directly
                return asyncio.run(calculate_ensemble_confidence(llm, prompt, num_samples))
        except Exception as e:
            logger.warning(f"Ensemble confidence calculation failed: {e}")
            return None


def extract_verbalized_confidence(text: str) -> Optional[float]:
    """Extract verbalized confidence from agent text output.

    Parses text for explicit confidence statements like "I am 85% sure"
    or "confidence: 75%".

    Args:
        text: Agent output text to parse

    Returns:
        Confidence score between 0-1, or None if no pattern found
    """
    if not text:
        return None

    text_upper = text.upper()

    for pattern in ConfidenceScorer.VERBALIZED_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            percentage = float(match.group(1))
            # Clamp to valid range
            percentage = max(0, min(100, percentage))
            return percentage / 100.0

    return None


async def calculate_ensemble_confidence(
    llm: Any, prompt: str, num_samples: int = 3
) -> Optional[float]:
    """Calculate confidence by measuring semantic consistency across samples.

    Samples the LLM multiple times and computes semantic similarity between
    responses. Higher consistency = higher confidence.

    Args:
        llm: LLM instance (LangChain format)
        prompt: Prompt to sample
        num_samples: Number of samples to generate (default: 3)

    Returns:
        Average semantic similarity as confidence score, or None if unavailable
    """
    try:
        import sentence_transformers
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.warning("sentence-transformers or sklearn not available for ensemble confidence")
        return None

    try:
        # Sample LLM multiple times
        responses = []
        for _ in range(num_samples):
            response = await llm.ainvoke(prompt) if hasattr(llm, 'ainvoke') else llm.invoke(prompt)
            responses.append(response.content if hasattr(response, 'content') else str(response))

        if len(responses) < 2:
            return None

        # Compute semantic embeddings
        model = sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = model.encode(responses)

        # Calculate pairwise cosine similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                similarities.append(sim)

        if not similarities:
            return None

        # Average similarity is confidence
        avg_similarity = float(np.mean(similarities))
        logger.debug(f"Ensemble confidence: {avg_similarity:.3f} from {len(similarities)} pairwise similarities")

        return avg_similarity

    except Exception as e:
        logger.warning(f"Ensemble confidence calculation failed: {e}")
        return None


def extract_token_confidence(llm_output: Any) -> Optional[float]:
    """Extract confidence from token log probabilities.

    Computes average probability of generated tokens using logprobs
    from LangChain LLM outputs.

    Args:
        llm_output: LLM output object (LangChain format)

    Returns:
        Average token probability, or None if logprobs unavailable
    """
    try:
        # Handle LangChain message objects
        if hasattr(llm_output, 'llm_output') and llm_output.llm_output:
            logprobs_data = llm_output.llm_output.get('logprobs')
            if logprobs_data:
                # Extract logprobs and convert to probabilities
                probs = []
                for lp_entry in logprobs_data:
                    if isinstance(lp_entry, dict):
                        # Handle dict format {token: logprob}
                        for token, lp in lp_entry.items():
                            if lp is not None:
                                probs.append(np.exp(lp))
                    elif lp_entry is not None:
                        # Handle direct logprob values
                        probs.append(np.exp(lp_entry))

                if probs:
                    avg_prob = float(np.mean(probs))
                    logger.debug(f"Token confidence: {avg_prob:.3f} from {len(probs)} tokens")
                    return avg_prob

        return None

    except Exception as e:
        logger.warning(f"Token confidence extraction failed: {e}")
        return None
