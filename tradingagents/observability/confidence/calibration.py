"""Confidence calibration tracking with Expected Calibration Error (ECE).

This module implements CalibrationTracker for tracking confidence calibration
over time, computing ECE, Brier scores, and reliability diagram data.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss

logger = logging.getLogger(__name__)


@dataclass
class CalibrationMetrics:
    """Calibration metrics from confidence-outcome pairs.

    Attributes:
        ece: Expected Calibration Error (lower is better)
        brier_score: Brier score loss (mean squared error, lower is better)
        sample_count: Number of confidence-outcome pairs
        is_well_calibrated: True if ECE < threshold (default 0.1)
        bin_data: Per-bin calibration data for reliability diagrams
    """

    ece: float
    brier_score: float
    sample_count: int
    is_well_calibrated: bool
    bin_data: List[Dict[str, float]]

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for serialization."""
        return {
            "ece": self.ece,
            "brier_score": self.brier_score,
            "sample_count": self.sample_count,
            "is_well_calibrated": self.is_well_calibrated,
            "bin_data": self.bin_data,
        }


class CalibrationTracker:
    """Tracks confidence calibration over time.

    Records confidence-outcome pairs and computes calibration metrics
    including Expected Calibration Error (ECE), Brier score, and
    reliability diagram data.

    Example:
        ```python
        tracker = CalibrationTracker(agent_name='market_analyst')

        # Record outcomes
        tracker.record_outcome(confidence=0.8, was_correct=True)
        tracker.record_outcome(confidence=0.6, was_correct=False)

        # Get metrics
        metrics = tracker.get_calibration_metrics()
        print(f"ECE: {metrics.ece:.4f}")
        print(f"Well calibrated: {metrics.is_well_calibrated}")
        ```
    """

    def __init__(self, agent_name: Optional[str] = None):
        """Initialize calibration tracker.

        Args:
            agent_name: Optional agent name for per-agent tracking
        """
        self.agent_name = agent_name
        self._confidences: List[float] = []
        self._outcomes: List[bool] = []
        logger.debug(f"CalibrationTracker initialized for agent: {agent_name}")

    def record_outcome(self, confidence: float, was_correct: bool) -> None:
        """Record a confidence-outcome pair.

        Args:
            confidence: Confidence score between 0.0 and 1.0
            was_correct: Whether the prediction was correct
        """
        if not 0.0 <= confidence <= 1.0:
            logger.warning(f"Confidence {confidence} not in [0, 1], clamping")
            confidence = max(0.0, min(1.0, confidence))

        self._confidences.append(confidence)
        self._outcomes.append(was_correct)
        logger.debug(
            f"Recorded outcome: confidence={confidence:.3f}, "
            f"correct={was_correct}, agent={self.agent_name}"
        )

    def get_calibration_metrics(
        self, n_bins: int = 10, calibration_threshold: float = 0.1
    ) -> CalibrationMetrics:
        """Calculate calibration metrics.

        Args:
            n_bins: Number of bins for ECE calculation
            calibration_threshold: ECE threshold for "well calibrated" status

        Returns:
            CalibrationMetrics with ECE, Brier score, and bin data
        """
        if len(self._confidences) == 0:
            logger.warning("No outcomes recorded, returning empty metrics")
            return CalibrationMetrics(
                ece=0.0,
                brier_score=0.0,
                sample_count=0,
                is_well_calibrated=False,
                bin_data=[],
            )

        # Convert outcomes to int (True=1, False=0) for sklearn
        y_true = np.array([int(o) for o in self._outcomes])
        y_prob = np.array(self._confidences)

        # Calculate ECE
        ece = self.expected_calibration_error(n_bins=n_bins)

        # Calculate Brier score
        brier = self.brier_score()

        # Get reliability diagram data
        bin_data = self.get_reliability_data(n_bins=n_bins)

        # Check if well calibrated
        is_well_calibrated = ece < calibration_threshold

        return CalibrationMetrics(
            ece=ece,
            brier_score=brier,
            sample_count=len(self._confidences),
            is_well_calibrated=is_well_calibrated,
            bin_data=bin_data,
        )

    def expected_calibration_error(self, n_bins: int = 10) -> float:
        """Compute Expected Calibration Error using sklearn.

        ECE measures the difference between predicted confidence and
        actual accuracy across confidence bins.

        Args:
            n_bins: Number of bins for discretization

        Returns:
            ECE as float (lower is better, 0.0 = perfectly calibrated)
        """
        if len(self._confidences) < n_bins:
            logger.debug(
                f"Insufficient samples ({len(self._confidences)}) for {n_bins} bins, "
                "returning ECE=0.0"
            )
            return 0.0

        # Check for edge case: all same confidence
        if len(set(self._confidences)) == 1:
            logger.debug("All confidences are identical, returning ECE=0.0")
            return 0.0

        try:
            y_true = np.array([int(o) for o in self._outcomes])
            y_prob = np.array(self._confidences)

            # Use sklearn's calibration_curve
            prob_true, prob_pred = calibration_curve(
                y_true, y_prob, n_bins=n_bins, strategy="uniform"
            )

            # Calculate weighted average of absolute calibration errors
            ece = 0.0
            for i in range(len(prob_true)):
                # Bin weight = proportion of samples in this bin
                bin_start = prob_pred[i] - (1.0 / n_bins) if i > 0 else 0.0
                bin_mask = (y_prob >= bin_start) & (y_prob <= prob_pred[i])
                bin_weight = np.sum(bin_mask) / len(y_prob)

                # Weighted calibration error
                ece += bin_weight * abs(prob_true[i] - prob_pred[i])

            return float(ece)

        except Exception as e:
            logger.error(f"ECE calculation failed: {e}")
            return 0.0

    def brier_score(self) -> float:
        """Compute Brier score (mean squared error).

        Lower is better. 0.0 = perfect predictions, 1.0 = worst possible.

        Returns:
            Brier score as float
        """
        if len(self._confidences) == 0:
            return 0.0

        try:
            y_true = [int(o) for o in self._outcomes]
            y_prob = self._confidences

            return float(brier_score_loss(y_true, y_prob))
        except Exception as e:
            logger.error(f"Brier score calculation failed: {e}")
            return 0.0

    def get_reliability_data(self, n_bins: int = 10) -> List[Dict[str, float]]:
        """Get per-bin calibration data for reliability diagrams.

        Returns structured data for plotting reliability diagrams.

        Args:
            n_bins: Number of bins

        Returns:
            List of dicts with bin_data: {
                'bin_lower': float,
                'bin_upper': float,
                'predicted_conf': float,
                'actual_accuracy': float,
                'sample_count': int
            }
        """
        if len(self._confidences) < n_bins:
            return []

        try:
            y_true = np.array([int(o) for o in self._outcomes])
            y_prob = np.array(self._confidences)

            prob_true, prob_pred = calibration_curve(
                y_true, y_prob, n_bins=n_bins, strategy="uniform"
            )

            bin_data = []
            for i in range(len(prob_pred)):
                bin_lower = max(0.0, prob_pred[i] - (1.0 / n_bins))
                bin_upper = min(1.0, prob_pred[i] + (1.0 / n_bins))

                # Count samples in this bin
                bin_mask = (y_prob >= bin_lower) & (y_prob < bin_upper)
                if i == len(prob_pred) - 1:  # Include upper bound for last bin
                    bin_mask = (y_prob >= bin_lower) & (y_prob <= bin_upper)
                sample_count = int(np.sum(bin_mask))

                bin_data.append(
                    {
                        "bin_lower": float(bin_lower),
                        "bin_upper": float(bin_upper),
                        "predicted_conf": float(prob_pred[i]),
                        "actual_accuracy": float(prob_true[i]),
                        "sample_count": sample_count,
                    }
                )

            return bin_data

        except Exception as e:
            logger.error(f"Reliability data calculation failed: {e}")
            return []

    def reset(self) -> None:
        """Clear all tracked outcomes."""
        self._confidences.clear()
        self._outcomes.clear()
        logger.debug(f"CalibrationTracker reset for agent: {self.agent_name}")

    def get_outcomes(self) -> Tuple[List[float], List[bool]]:
        """Return all recorded confidence-outcome pairs.

        Returns:
            Tuple of (confidences, outcomes)
        """
        return list(self._confidences), list(self._outcomes)

    @property
    def sample_count(self) -> int:
        """Return number of recorded outcomes."""
        return len(self._confidences)


def calculate_ece(
    y_true: List[bool], y_prob: List[float], n_bins: int = 10
) -> float:
    """Calculate Expected Calibration Error from binary outcomes and probabilities.

    Helper function for computing ECE without creating a tracker instance.

    Args:
        y_true: True binary labels (True/False or 1/0)
        y_prob: Predicted probabilities (0.0 to 1.0)
        n_bins: Number of bins for discretization

    Returns:
        ECE as float (lower is better)
    """
    if len(y_true) != len(y_prob):
        raise ValueError(f"Length mismatch: {len(y_true)} != {len(y_prob)}")

    if len(y_true) == 0:
        return 0.0

    if len(y_true) < n_bins:
        logger.warning(f"Insufficient samples ({len(y_true)}) for {n_bins} bins")
        return 0.0

    try:
        # Convert to numpy arrays
        y_true_arr = np.array([int(o) for o in y_true])
        y_prob_arr = np.array(y_prob)

        # Use sklearn calibration_curve
        prob_true, prob_pred = calibration_curve(
            y_true_arr, y_prob_arr, n_bins=n_bins, strategy="uniform"
        )

        # Calculate weighted ECE
        ece = 0.0
        for i in range(len(prob_true)):
            bin_start = max(0.0, prob_pred[i] - (1.0 / n_bins) if i > 0 else 0.0)
            bin_mask = (y_prob_arr >= bin_start) & (y_prob_arr <= prob_pred[i])
            bin_weight = np.sum(bin_mask) / len(y_prob_arr)
            ece += bin_weight * abs(prob_true[i] - prob_pred[i])

        return float(ece)

    except Exception as e:
        logger.error(f"ECE calculation failed: {e}")
        return 0.0
