# Phase 2: Confidence & Uncertainty - Research

**Researched:** 2026-02-27
**Domain:** LLM Confidence Scoring & Uncertainty Quantification for Multi-Agent Trading Systems
**Confidence:** MEDIUM

## Summary

This phase implements confidence scoring and uncertainty quantification for the multi-agent trading system. Each agent (analysts, researchers, traders, judges) will report confidence scores that are aggregated into system-level confidence, with calibration tracking to assess reliability over time. The foundation from Phase 1 provides the DecisionRecord model with a placeholder `confidence` field and the StateExtractor for parsing agent outputs.

**Primary recommendation:** Use ensemble-based confidence estimation with semantic consistency scoring for LLM outputs, implement Bayesian aggregation for multi-agent confidence fusion, and track calibration metrics (Expected Calibration Error) to ensure confidence scores match actual accuracy.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| CONF-01 | Each agent reports a confidence score with its output | ConfidenceScorer with multiple estimation methods (verbalized, ensemble-based, semantic consistency) |
| CONF-02 | System aggregates individual agent confidences into system-level confidence | Bayesian aggregation, weighted averaging, and robust aggregation methods |
| CONF-03 | Confidence calibration tracking records whether confidence levels match actual accuracy | Calibration metrics (ECE, reliability diagrams), historical tracking in SQLite |
| CONF-04 | Users can view confidence history to assess system reliability | Query interface for calibration data, confidence trend analysis |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.0+ | Type-safe confidence data models | Already used in DecisionRecord, provides validation for confidence scores (0.0-1.0) |
| NumPy | 1.24+ | Numerical computations for aggregation | Standard for array operations, statistical calculations |
| Scikit-learn | 1.3+ | Calibration metrics and reliability diagrams | `calibration_error`, `calibration_curve` for Expected Calibration Error |
| LangChain | 0.1+ | LLM confidence extraction | Already integrated, provides access to token probabilities and logprobs |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SentimentTransformers | Latest | Semantic similarity for ensemble consistency | When implementing semantic entropy-based confidence |
| SQLite | 3.40+ | Calibration history storage | Already from Phase 1, stores confidence-outcome pairs |
| Plotly | 5.18+ | Calibration visualization | Optional: for reliability diagrams and calibration curves |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Verbalized confidence | Token probability-based | Verbalized easier but less accurate; token probabilities more objective but require logprob access |
| Semantic entropy | Monte Carlo dropout | Semantic entropy more accurate for text; MC dropout faster but requires model modification |
| Bayesian aggregation | Simple averaging | Bayesian more sophisticated; averaging simpler and interpretable |

**Installation:**
```bash
# Core dependencies (likely already installed)
pip install pydantic numpy scikit-learn langchain

# For semantic consistency scoring (optional)
pip install sentence-transformers

# For visualization (deferred)
pip install plotly
```

## Architecture Patterns

### Recommended Project Structure

```
tradingagents/observability/
├── confidence/
│   ├── __init__.py
│   ├── scorer.py              # ConfidenceScorer class
│   ├── aggregation.py         # Confidence aggregation methods
│   ├── calibration.py         # Calibration metrics tracking
│   └── models.py              # Pydantic models for confidence data
├── storage/
│   └── sqlite_backend.py      # Extend with confidence queries
└── instrumentation/
    └── state_extractor.py     # Extend to extract confidence
```

### Pattern 1: Confidence Extraction from LLM Outputs

**What:** Extract confidence scores from agent responses using multiple methods

**When to use:** When processing agent outputs in StateExtractor

**Three extraction methods:**

1. **Verbalized Confidence** - Parse explicit confidence statements
   ```python
   # Source: Web search on LLM confidence scoring 2025
   def extract_verbalized_confidence(text: str) -> Optional[float]:
       """Extract confidence from phrases like "I am 85% sure"."""
       patterns = [
           r"(\d+)%\s*sure",
           r"(\d+)%\s*confident",
           r"confidence[:\s]+(\d+)%"
       ]
       for pattern in patterns:
           match = re.search(pattern, text, re.IGNORECASE)
           if match:
               return float(match.group(1)) / 100.0
       return None
   ```

2. **Ensemble Consistency** - Measure agreement across multiple samples
   ```python
   # Source: Semantic entropy research (ICLR 2023)
   async def calculate_ensemble_confidence(
       llm, prompt: str, num_samples: int = 5
   ) -> float:
       """Calculate confidence by measuring semantic consistency across samples."""
       responses = await asyncio.gather(*[
           llm.ainvoke(prompt) for _ in range(num_samples)
       ])

       # Compute pairwise semantic similarities
       from sentence_transformers import SentenceTransformer
       model = SentenceTransformer('all-MiniLM-L6-v2')
       embeddings = model.encode([r.content for r in responses])

       # Confidence = average pairwise similarity
       similarities = []
       for i in range(len(embeddings)):
           for j in range(i+1, len(embeddings)):
               sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
               similarities.append(sim)

       return float(np.mean(similarities)) if similarities else 0.5
   ```

3. **Token Probability Analysis** - Use logprobs if available
   ```python
   # Source: LangChain documentation on logprobs
   def extract_token_confidence(llm_output) -> Optional[float]:
       """Extract confidence from token logprobs."""
       if hasattr(llm_output, 'llm_output') and 'logprobs' in llm_output.llm_output:
           # Average probability of top tokens
           logprobs = llm_output.llm_output['logprobs']
           probs = [np.exp(lp) for lp in logprobs if lp is not None]
           return float(np.mean(probs)) if probs else None
       return None
   ```

### Pattern 2: Multi-Agent Confidence Aggregation

**What:** Combine individual agent confidences into system-level score

**When to use:** When final decision requires aggregating multiple agent opinions

**Three aggregation methods:**

1. **Weighted Average** - Weight by historical accuracy
   ```python
   # Source: Web search on forecast aggregation
   def weighted_aggregation(
       confidences: Dict[str, float],
       weights: Dict[str, float]
   ) -> float:
       """Aggregate confidences using accuracy-based weights."""
       total_weight = sum(weights.values())
       return sum(c * w for c, w in zip(confidences.values(), weights.values())) / total_weight
   ```

2. **Bayesian Aggregation** - Treat confidence as evidence
   ```python
   # Source: SIMBA UQ research (CSDN blog)
   def bayesian_aggregation(
       confidences: Dict[str, float],
       prior_alpha: float = 1.0,
       prior_beta: float = 1.0
   ) -> float:
       """Aggregate using Bayesian updating with Beta prior."""
       # Treat each confidence as evidence
       posterior_alpha = prior_alpha + sum(confidences.values())
       posterior_beta = prior_beta + sum(1.0 - c for c in confidences.values())

       # Expected value of Beta distribution
       return posterior_alpha / (posterior_alpha + posterior_beta)
   ```

3. **Minimum Consensus** - Use lowest confidence (conservative)
   ```python
   # Source: Research summary - graded trust routing
   def consensus_aggregation(confidences: Dict[str, float]) -> float:
       """Aggregate using minimum consensus (weakest link)."""
       return min(confidences.values()) if confidences else 0.5
   ```

### Pattern 3: Calibration Tracking

**What:** Track whether confidence scores match actual accuracy over time

**When to use:** Continuously after outcomes are calculated (Phase 5)

**Implementation:**

```python
# Source: Scikit-learn calibration documentation
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss

class CalibrationTracker:
    """Tracks calibration of confidence scores."""

    def __init__(self):
        self.confidences: List[float] = []
        self.outcomes: List[bool] = []  # True if decision was correct

    def record_outcome(self, confidence: float, was_correct: bool):
        """Record a confidence-outcome pair."""
        self.confidences.append(confidence)
        self.outcomes.append(was_correct)

    def expected_calibration_error(self, n_bins: int = 10) -> float:
        """Calculate Expected Calibration Error (ECE)."""
        if len(self.confidences) < n_bins:
            return 0.0

        # Bin confidences and compare to accuracy
        prob_true, prob_pred = calibration_curve(
            self.outcomes, self.confidences, n_bins=n_bins
        )

        # Weighted average of calibration errors
        ece = 0.0
        for i in range(len(prob_true)):
            ece += abs(prob_true[i] - prob_pred[i]) / len(prob_true)

        return ece

    def is_well_calibrated(self, threshold: float = 0.1) -> bool:
        """Check if ECE is within acceptable threshold."""
        return self.expected_calibration_error() < threshold
```

### Pattern 4: Graded Trust Routing

**What:** Route decisions based on confidence level

**When to use:** To implement selective prediction (refuse when uncertain)

```python
# Source: Research summary on selective prediction
class ConfidenceRouter:
    """Routes decisions based on confidence levels."""

    HIGH_CONFIDENCE = 0.8   # Auto-execute
    MEDIUM_CONFIDENCE = 0.5 # Human review
    LOW_CONFIDENCE = 0.5    # Defer

    def route(self, confidence: float) -> str:
        """Determine action based on confidence."""
        if confidence >= self.HIGH_CONFIDENCE:
            return "auto_execute"
        elif confidence >= self.MEDIUM_CONFIDENCE:
            return "human_review"
        else:
            return "defer"
```

### Anti-Patterns to Avoid

- **Overconfidence from RLHF:** Models fine-tuned with RL tend to be overconfident. Mitigation: Track calibration, use temperature scaling
- **Single-number confidence:** Always show confidence intervals or ranges, not single points
- **Ignoring semantic equivalence:** Different phrasings of same meaning should not increase uncertainty. Use semantic entropy
- **Calibration without outcomes:** Cannot assess calibration until outcomes are known (Phase 5)
- **Hardcoded thresholds:** Confidence thresholds should be tunable per deployment

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Calibration metrics | Manual ECE calculation | `sklearn.calibration.calibration_curve` | Well-tested, handles edge cases (empty bins, edge cases) |
| Semantic similarity | Custom cosine similarity | `sentence-transformers` | Pre-trained models capture semantic nuances, not just word overlap |
| Statistical distributions | Manual Beta distribution | `scipy.stats.beta` | Numerical stability, comprehensive API |
| Database queries | Raw SQL queries | SQLAlchemy ORM or existing SQLite backend | Type-safe, prevents SQL injection, easier to test |

**Key insight:** Building custom statistical functions is error-prone. Use battle-tested libraries for metrics and calculations. Focus research effort on confidence extraction methods, not statistical plumbing.

## Common Pitfalls

### Pitfall 1: Uncalibrated Confidence Misleads Users

**What goes wrong:** System reports "80% confidence" but is only correct 40% of the time. Users lose trust or make bad decisions.

**Why it happens:** LLMs tend to be overconfident, especially after RLHF fine-tuning. Verbalized confidence ("I'm 80% sure") doesn't correlate with actual accuracy.

**How to avoid:**
- Track calibration from day one (CONF-03)
- Use Expected Calibration Error (ECE) as primary metric
- Show calibration status to users: "80% confidence (historically 75% accurate)"
- Implement temperature scaling for post-hoc calibration

**Warning signs:** Confidence scores consistently above 0.7, calibration ECE > 0.1, users report "system says confident but is wrong"

### Pitfall 2: Confusing Prediction with Certainty

**What goes wrong:** Showing "AAPL will go up" without indicating uncertainty. Users treat predictions as facts.

**Why it happens:** Binary decisions (BUY/SELL) lose uncertainty information.

**How to avoid:**
- Always show confidence alongside prediction
- Use visual encoding: transparency, fuzziness, error bars
- Color code: green = high confidence, red = low confidence
- Explicit "I don't know" state when confidence < 0.4

**Warning signs:** Users act on predictions without considering risk, no visual indicators of uncertainty

### Pitfall 3: Ensemble Sampling Too Expensive

**What goes wrong:** Calculating confidence by sampling 5 LLM responses adds 5x latency to decisions.

**Why it happens:** Semantic consistency requires multiple forward passes.

**How to avoid:**
- Use verbalized confidence first (fast but less accurate)
- Fall back to ensemble only when verbalized unavailable
- Cache ensemble results for similar inputs
- Use smaller models for confidence estimation
- Implement async sampling

**Warning signs:** Decision latency increases by >2x, user complaints about speed

### Pitfall 4: Ignoring Agent Heterogeneity

**What goes wrong:** Treating all agent confidences equally when some agents are historically more reliable.

**Why it happens:** Simple aggregation doesn't account for past performance.

**How to avoid:**
- Track per-agent calibration metrics
- Use weighted aggregation with accuracy-based weights
- Update weights dynamically as outcomes arrive
- Show agent-level confidence in UI

**Warning signs:** Some agents consistently over/under-perform their confidence, users distrust specific agents

## Code Examples

Verified patterns from official sources:

### Expected Calibration Error Calculation

```python
# Source: Scikit-learn documentation
from sklearn.calibration import calibration_curve
import numpy as np

def calculate_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Calculate Expected Calibration Error.

    Args:
        y_true: True binary labels (0 or 1)
        y_prob: Predicted probabilities
        n_bins: Number of bins to discretize probabilities

    Returns:
        Expected Calibration Error
    """
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins)

    # Calculate weighted average of calibration errors
    ece = 0.0
    for i in range(len(prob_true)):
        bin_weight = len(y_true[(prob_pred[i-1] if i > 0 else 0) <= y_prob])
        bin_weight /= len(y_true)
        ece += bin_weight * abs(prob_true[i] - prob_pred[i])

    return ece
```

### Pydantic Confidence Model

```python
# Source: Web search on Pydantic confidence models
from pydantic import BaseModel, Field, validator

class AgentConfidence(BaseModel):
    """Confidence score with validation."""

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )
    method: str = Field(
        description="Method used to calculate confidence"
    )
    metadata: dict = Field(default_factory=dict)

    @validator('score')
    def validate_score(cls, v):
        """Ensure score is valid."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0 and 1')
        return v
```

### Semantic Similarity for Consistency

```python
# Source: Sentence-Transformers documentation
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def semantic_consistency(texts: list[str]) -> float:
    """Calculate semantic consistency across texts.

    Higher values indicate more semantic agreement.
    """
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(texts)

    # Calculate pairwise cosine similarities
    similarities = cosine_similarity(embeddings)

    # Average upper triangle (excluding diagonal)
    n = len(similarities)
    avg_sim = sum(similarities[i][j] for i in range(n) for j in range(i+1, n))
    avg_sim /= (n * (n - 1)) / 2 if n > 1 else 1

    return float(avg_sim)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Verbalized confidence only | Multi-method (verbalized + ensemble + semantic) | 2023-2024 | More robust confidence estimation |
| Single-number confidence | Confidence intervals + uncertainty quantification | 2024-2025 | Better communication of uncertainty |
| Post-hoc calibration | Continuous tracking with adaptive thresholds | 2025 | Calibration improves over time |
| Simple averaging | Bayesian aggregation with evidence updating | 2024 | More sophisticated multi-agent fusion |

**Deprecated/outdated:**
- **Temperature-only confidence:** Adjusting temperature alone doesn't calibrate confidence
- **Majority voting for confidence:** Can amplify overconfident agents
- **Static confidence thresholds:** Should adapt based on historical performance

## Open Questions

1. **Confidence extraction from existing prompts**
   - What we know: Agents currently output decisions without explicit confidence
   - What's unclear: Whether to modify agent prompts to request confidence, or extract post-hoc
   - Recommendation: Start with post-hoc extraction (less invasive), evaluate accuracy, then consider prompt modifications if needed

2. **Optimal number of ensemble samples**
   - What we know: More samples = better consistency measurement but higher latency
   - What's unclear: Tradeoff point for this specific use case
   - Recommendation: Start with n=3 (balance), measure latency impact, adjust based on user feedback

3. **Calibration calculation before Phase 5**
   - What we know: Calibration requires outcome data (Phase 5)
   - What's unclear: How to validate calibration works without historical outcomes
   - Recommendation: Implement calibration infrastructure, use synthetic data for testing, validate with real outcomes in Phase 5

4. **Storage format for confidence data**
   - What we know: SQLite from Phase 1, DecisionRecord has confidence field
   - What's unclear: Whether separate confidence history table needed for efficient queries
   - Recommendation: Store confidence in DecisionRecord for now, add separate calibration table if queries become slow

## Sources

### Primary (HIGH confidence)
- **Scikit-learn Calibration Documentation** - `calibration_curve`, ECE calculation patterns
- **LangChain Documentation** - Logprob access, token probability extraction
- **Pydantic Documentation** - Field validation for confidence scores (ge=0, le=1)
- **Sentence-Transformers Documentation** - Semantic similarity calculations
- **Phase 1 Implementation** - DecisionRecord model, StateExtractor pattern, SQLite storage

### Secondary (MEDIUM confidence)
- **"Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation"** (ICLR 2023) - Semantic entropy methodology
- **"Uncertainty Quantification and Confidence Calibration in Large Language Models: A Survey"** (ArXiv, June 2025) - Comprehensive UQ methods survey
- **"Improving Uncertainty Quantification in Large Language Models via Semantic Embeddings"** (2024) - Embedding-based uncertainty estimation
- **BEYOND BINARY REWARDS: Training LMs to Reason About Their Uncertainty** - RL-based calibration approaches
- **QuantAgent: Multi-Agent LLMs for High-Frequency Trading** (ArXiv, Sept 2025) - Multi-agent confidence patterns

### Tertiary (LOW confidence)
- **Calibrating LLM Confidence by Probing Perturbed Representations** (ArXiv, May 2025) - Calibration-tuning tradeoffs
- **Ensemble Methods for Uncertainty Calibration** (CSDN, Oct 2025) - Dirichlet calibration techniques
- **Bayesian Aggregation methods** - Various sources on forecast aggregation, need implementation validation

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - Pydantic/NumPy/sklearn well-established, but confidence extraction methods vary in practice
- Architecture: MEDIUM - Patterns from research papers validated, but need implementation testing for this specific use case
- Pitfalls: HIGH - Well-documented in research (overconfidence, semantic equivalence issues), codebase analysis confirms no existing calibration

**Research date:** 2026-02-27
**Valid until:** 2026-04-15 (60 days - confidence scoring is active research area)

**Gaps requiring validation during implementation:**
- Ensemble sampling latency impact on real trading decisions
- Accuracy of verbalized confidence extraction for current agent prompts
- Optimal aggregation method for 8+ agents with varying reliability
- SQLite query performance for calibration history at scale
