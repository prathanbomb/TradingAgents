"""Debate explorer module for parsing and visualizing agent debates.

This module provides tools for extracting structured debate data from
DecisionRecord.debate_state, enabling users to explore bull/bear
researcher arguments and risk analyst debates with progressive disclosure.

Key components:
- DebateParser: Extract structured arguments from debate_state
- DebateSummarizer: Generate progressive disclosure summaries
- DebateExplorer: Query and filter debates from storage
- DebateRenderer: Display debates with progressive disclosure levels
- JudgmentVisualizer: Analyze debate resolution and judgment reasoning
- JudgmentRenderer: Render judgment visualizations with progressive disclosure
"""

from tradingagents.observability.debate.explorer import DebateExplorer, DebateRenderer
from tradingagents.observability.debate.models import (
    Argument,
    Debate,
    DebateSummary,
    Judgment,
    JudgmentView,
    DecisionInfluence
)
from tradingagents.observability.debate.parser import DebateParser
from tradingagents.observability.debate.summarizer import DebateSummarizer
from tradingagents.observability.debate.judgment import (
    JudgmentVisualizer,
    JudgmentRenderer
)

__all__ = [
    "Argument",
    "Judgment",
    "Debate",
    "DebateSummary",
    "JudgmentView",
    "DecisionInfluence",
    "DebateParser",
    "DebateSummarizer",
    "DebateExplorer",
    "DebateRenderer",
    "JudgmentVisualizer",
    "JudgmentRenderer",
]
