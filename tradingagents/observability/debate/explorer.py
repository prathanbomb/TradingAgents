"""Debate explorer for querying and filtering debates with progressive disclosure.

This module provides DebateExplorer for retrieving debates from storage by various
criteria and DebateRenderer for displaying debates with progressive disclosure levels.
"""

import logging
from datetime import datetime
from typing import Dict, List, Literal, Optional, Union

from tradingagents.observability.debate.models import Argument, Debate, DebateSummary, Judgment
from tradingagents.observability.debate.parser import DebateParser
from tradingagents.observability.debate.summarizer import DebateSummarizer
from tradingagents.observability.storage.sqlite_backend import SQLiteDecisionStore

logger = logging.getLogger(__name__)


class DebateExplorer:
    """Query and filter debates for exploration.

    Provides interface for retrieving debates from storage by various criteria
    and returning DebateSummary objects for progressive disclosure display.
    """

    def __init__(
        self,
        store: SQLiteDecisionStore,
        parser: DebateParser,
        summarizer: Optional[DebateSummarizer] = None,
    ):
        """Initialize explorer with storage and parsing components.

        Args:
            store: SQLiteDecisionStore from Phase 1 for retrieving DecisionRecord
            parser: DebateParser from 04-01 for parsing debate_state
            summarizer: Optional DebateSummarizer from 04-02. If None, returns
                full Debate objects without summarization.
        """
        self.store = store
        self.parser = parser
        self.summarizer = summarizer
        logger.debug(
            f"DebateExplorer initialized: summarizer={'enabled' if summarizer else 'disabled'}"
        )

    def get_debates(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        debate_type: Optional[Literal["investment", "risk"]] = None,
        limit: int = 100,
    ) -> List[Union[DebateSummary, Debate]]:
        """Retrieve debates matching the specified criteria.

        Queries DecisionRecord from storage, filters by criteria, parses
        debate_state, and optionally summarizes for progressive disclosure.

        Args:
            ticker: Filter by stock ticker symbol (e.g., "AAPL")
            start_date: Filter by trade_date >= start_date (YYYY-MM-DD format)
            end_date: Filter by trade_date <= end_date (YYYY-MM-DD format)
            debate_type: Filter by debate type ("investment" or "risk")
            limit: Maximum number of debates to return (default: 100)

        Returns:
            List of DebateSummary objects (or Debate if summarizer=None)
        """
        # Validate date format
        if start_date:
            self._validate_date_format(start_date)
        if end_date:
            self._validate_date_format(end_date)

        # Query records with debate_state from storage
        records = self.store.query_debates(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            has_debate=True,
            limit=limit,
        )

        # Parse and optionally summarize debates
        results = []
        for record in records:
            try:
                debate_summary = self._parse_and_summarize_record(record)
                if debate_summary:
                    # Filter by debate_type if specified
                    if debate_type is None or debate_summary.debate_type == debate_type:
                        results.append(debate_summary)
            except Exception as e:
                logger.warning(f"Failed to process debate for record {record.get('decision_id')}: {e}")
                continue

        logger.debug(f"Retrieved {len(results)} debates matching criteria")
        return results

    def get_debate_by_run_id(self, run_id: str) -> Optional[Union[DebateSummary, Debate]]:
        """Retrieve a specific debate by its run_id.

        Args:
            run_id: Run identifier linking debate to DecisionTrail

        Returns:
            DebateSummary if found, None if not found
        """
        # Get records by run_id
        records = self.store.get_decision_records_by_run_id(run_id)

        if not records:
            logger.debug(f"No records found for run_id: {run_id}")
            return None

        # Find first record with debate_state
        for record in records:
            debate_state_json = record.get("debate_state")
            if debate_state_json:
                try:
                    return self._parse_and_summarize_record(record)
                except Exception as e:
                    logger.warning(f"Failed to parse debate for run_id {run_id}: {e}")
                    continue

        logger.debug(f"No debate_state found for run_id: {run_id}")
        return None

    def get_debates_by_judgment(
        self,
        judgment_pattern: str,
        debate_type: Optional[Literal["investment", "risk"]] = None,
    ) -> List[Union[DebateSummary, Debate]]:
        """Find debates where judge decision matches pattern.

        Useful for exploring all debates where judge favored bull case,
        or all risk debates marked as "risky".

        Args:
            judgment_pattern: Substring to match in judge_decision text
            debate_type: Optional filter by debate type

        Returns:
            List of DebateSummary objects matching the judgment pattern
        """
        # Query debates with judgment pattern
        records = self.store.query_debates(
            judgment_pattern=judgment_pattern,
            has_debate=True,
            limit=500,  # Higher limit for search results
        )

        # Parse and optionally summarize
        results = []
        for record in records:
            try:
                debate_summary = self._parse_and_summarize_record(record)
                if debate_summary:
                    # Filter by debate_type if specified
                    if debate_type is None or debate_summary.debate_type == debate_type:
                        results.append(debate_summary)
            except Exception as e:
                logger.warning(f"Failed to process debate for record {record.get('decision_id')}: {e}")
                continue

        logger.debug(
            f"Found {len(results)} debates matching judgment pattern: {judgment_pattern}"
        )
        return results

    def search_arguments(
        self,
        query: str,
        ticker: Optional[str] = None,
        debate_type: Optional[Literal["investment", "risk"]] = None,
    ) -> List[Union[DebateSummary, Debate]]:
        """Search for debates containing specific argument text.

        Full-text search across all argument content to find debates
        mentioning specific topics (e.g., "P/E ratio", "earnings beat").

        Args:
            query: Search query string
            ticker: Optional filter by ticker
            debate_type: Optional filter by debate type

        Returns:
            List of DebateSummary where arguments match query
        """
        # Search debate content
        records = self.store.search_debate_content(query=query, debate_field=None)

        # Filter by ticker if specified
        if ticker:
            records = [r for r in records if r.get("ticker") == ticker]

        # Parse and optionally summarize
        results = []
        for record in records:
            try:
                debate_summary = self._parse_and_summarize_record(record)
                if debate_summary:
                    # Filter by debate_type if specified
                    if debate_type is None or debate_summary.debate_type == debate_type:
                        results.append(debate_summary)
            except Exception as e:
                logger.warning(f"Failed to process debate for record {record.get('decision_id')}: {e}")
                continue

        logger.debug(f"Found {len(results)} debates matching query: {query}")
        return results

    def _parse_and_summarize_record(
        self, record: Dict
    ) -> Optional[Union[DebateSummary, Debate]]:
        """Parse debate_state from record and optionally summarize.

        Args:
            record: DecisionRecord dict from storage

        Returns:
            DebateSummary if summarizer available, Debate otherwise, None if parsing fails
        """
        import json

        debate_state_json = record.get("debate_state")
        if not debate_state_json:
            return None

        try:
            debate_state = json.loads(debate_state_json)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse debate_state JSON: {e}")
            return None

        # Detect debate type and parse
        run_id = record.get("run_id", "unknown")
        ticker = record.get("ticker", "UNKNOWN")
        trade_date = record.get("trade_date", datetime.utcnow().strftime("%Y-%m-%d"))

        # Check if investment debate (has bull_history)
        if "bull_history" in debate_state:
            from tradingagents.observability.models.decision_record import InvestDebateState

            debate_state_obj = InvestDebateState(**debate_state)
            debate = self.parser.parse_investment_debate(
                debate_state=debate_state_obj,
                run_id=run_id,
                ticker=ticker,
                trade_date=trade_date,
            )
        # Check if risk debate (has risky_history)
        elif "risky_history" in debate_state:
            debate = self.parser.parse_risk_debate(
                risk_debate_state=debate_state,
                run_id=run_id,
                ticker=ticker,
                trade_date=trade_date,
            )
        else:
            logger.warning(f"Unknown debate type for record {record.get('decision_id')}")
            return None

        # Summarize if summarizer available
        if self.summarizer:
            return self.summarizer.summarize_debate(debate)
        else:
            return debate

    def _validate_date_format(self, date_str: str) -> None:
        """Validate date string is in YYYY-MM-DD format.

        Args:
            date_str: Date string to validate

        Raises:
            ValueError: If date format is invalid
        """
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid date format: {date_str}. Expected YYYY-MM-DD format."
            ) from e


class DebateRenderer:
    """Render debates for display with progressive disclosure.

    Provides text-based rendering of DebateSummary with expandable sections
    for key points and full transcript (similar to TrailRenderer from 03-04).
    """

    # Speaker emoji indicators
    SPEAKER_EMOJIS: Dict[str, str] = {
        "Bull Analyst": "🐂",
        "Bear Analyst": "🐻",
        "Risky Analyst": "⚠️",
        "Safe Analyst": "🛡️",
        "Neutral Analyst": "⚖️",
        "Investment Judge": "🏛️",
        "Risk Judge": "🏛️",
    }

    def __init__(self, max_content_length: int = 200):
        """Initialize debate renderer with display preferences.

        Args:
            max_content_length: Maximum characters of argument content to show
                in timeline view before truncating.
        """
        self.max_content_length = max_content_length
        logger.debug(f"DebateRenderer initialized: max_content_length={max_content_length}")

    def render_summary(
        self,
        debate_summary: DebateSummary,
        level: Literal[1, 2, 3] = 1,
    ) -> str:
        """Render debate at specified disclosure level.

        Level 1: Summary only (1-2 sentences)
        Level 2: Summary + key points (expandable)
        Level 3: Summary + key points + full transcript

        Args:
            debate_summary: DebateSummary to render
            level: Disclosure level (1-3)

        Returns:
            Formatted text representation of debate
        """
        lines = []

        # Header with metadata
        lines.append(f"Debate: {debate_summary.debate_id[:8]}...")
        lines.append(f"Type: {debate_summary.debate_type}")
        lines.append(f"Turns: {debate_summary.total_turns} | Arguments: {debate_summary.total_arguments}")
        lines.append("=" * 80)
        lines.append("")

        # Level 1: Summary (always shown)
        lines.append("## Summary")
        lines.append(debate_summary.summary)
        lines.append("")

        # Judgment
        if debate_summary.judgment_summary:
            lines.append("## Judgment")
            lines.append(debate_summary.judgment_summary)
            lines.append("")

        # Level 2: Key points (expandable)
        if level >= 2:
            lines.append("## Key Arguments")
            lines.append("")

            if debate_summary.debate_type == "investment":
                if debate_summary.bull_key_points:
                    lines.append(f"{self.SPEAKER_EMOJIS.get('Bull Analyst', '🐂')} Bull Analyst:")
                    for point in debate_summary.bull_key_points:
                        lines.append(f"  • {point}")
                    lines.append("")

                if debate_summary.bear_key_points:
                    lines.append(f"{self.SPEAKER_EMOJIS.get('Bear Analyst', '🐻')} Bear Analyst:")
                    for point in debate_summary.bear_key_points:
                        lines.append(f"  • {point}")
                    lines.append("")

            elif debate_summary.debate_type == "risk":
                if debate_summary.risky_key_points:
                    lines.append(f"{self.SPEAKER_EMOJIS.get('Risky Analyst', '⚠️')} Risky Analyst:")
                    for point in debate_summary.risky_key_points:
                        lines.append(f"  • {point}")
                    lines.append("")

                if debate_summary.safe_key_points:
                    lines.append(f"{self.SPEAKER_EMOJIS.get('Safe Analyst', '🛡️')} Safe Analyst:")
                    for point in debate_summary.safe_key_points:
                        lines.append(f"  • {point}")
                    lines.append("")

                if debate_summary.neutral_key_points:
                    lines.append(
                        f"{self.SPEAKER_EMOJIS.get('Neutral Analyst', '⚖️')} Neutral Analyst:"
                    )
                    for point in debate_summary.neutral_key_points:
                        lines.append(f"  • {point}")
                    lines.append("")

        # Level 3: Full transcript (expandable)
        if level >= 3 and debate_summary.full_transcript:
            lines.append("## Full Transcript")
            lines.append(debate_summary.full_transcript)

        return "\n".join(lines)

    def render_timeline(self, debate: Debate) -> str:
        """Render debate as chronological argument timeline.

        Shows each argument in order with speaker, turn number,
        and truncated content (similar to TrailRenderer timeline).

        Args:
            debate: Full Debate object with all arguments

        Returns:
            Formatted timeline text
        """
        lines = []

        # Header
        lines.append(f"Debate Timeline: {debate.ticker} ({debate.debate_type})")
        lines.append(f"Date: {debate.trade_date} | Run ID: {debate.run_id}")
        lines.append(f"Total Turns: {debate.total_turns}")
        lines.append("=" * 80)
        lines.append("")

        # Arguments in chronological order
        for arg in debate.arguments:
            speaker_emoji = self.SPEAKER_EMOJIS.get(arg.speaker, "💬")
            lines.append(f"Turn {arg.turn_number} - {speaker_emoji} {arg.speaker}")

            # Truncate content if needed
            content = arg.content
            if len(content) > self.max_content_length:
                content = content[: self.max_content_length] + "..."
            lines.append(content)
            lines.append("")

        # Judgment
        if debate.judgment:
            lines.append(self.render_judgment(debate.judgment))

        return "\n".join(lines)

    def render_judgment(self, judgment: Judgment) -> str:
        """Render judgment section prominently.

        Highlights judge's decision to show how debate was resolved.

        Args:
            judgment: Judgment object to render

        Returns:
            Formatted judgment text
        """
        lines = []

        judge_emoji = self.SPEAKER_EMOJIS.get(judgment.judge, "🏛️")
        lines.append(f"{judge_emoji} Judgment: {judgment.judge}")
        lines.append("-" * 80)
        lines.append(judgment.decision)

        if judgment.reasoning:
            lines.append("")
            lines.append("Reasoning:")
            lines.append(judgment.reasoning)

        return "\n".join(lines)

    def render_markdown(
        self,
        debate_summary: DebateSummary,
        level: Literal[1, 2, 3] = 1,
    ) -> str:
        """Render debate as Markdown document for export.

        Args:
            debate_summary: DebateSummary to render
            level: Disclosure level (1-3)

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header
        lines.append(f"# Debate: {debate_summary.debate_type.upper()}")
        lines.append("")
        lines.append(f"**Debate ID:** `{debate_summary.debate_id}`")
        lines.append(f"**Type:** {debate_summary.debate_type}")
        lines.append(f"**Turns:** {debate_summary.total_turns}")
        lines.append(f"**Arguments:** {debate_summary.total_arguments}")
        lines.append("")

        # Level 1: Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(debate_summary.summary)
        lines.append("")

        # Judgment
        if debate_summary.judgment_summary:
            lines.append("## Judgment")
            lines.append("")
            lines.append(debate_summary.judgment_summary)
            lines.append("")

        # Level 2: Key points
        if level >= 2:
            lines.append("## Key Arguments")
            lines.append("")

            if debate_summary.debate_type == "investment":
                if debate_summary.bull_key_points:
                    lines.append(f"{self.SPEAKER_EMOJIS.get('Bull Analyst', '🐂')} Bull Analyst")
                    for point in debate_summary.bull_key_points:
                        lines.append(f"- {point}")
                    lines.append("")

                if debate_summary.bear_key_points:
                    lines.append(f"{self.SPEAKER_EMOJIS.get('Bear Analyst', '🐻')} Bear Analyst")
                    for point in debate_summary.bear_key_points:
                        lines.append(f"- {point}")
                    lines.append("")

            elif debate_summary.debate_type == "risk":
                if debate_summary.risky_key_points:
                    lines.append(f"{self.SPEAKER_EMOJIS.get('Risky Analyst', '⚠️')} Risky Analyst")
                    for point in debate_summary.risky_key_points:
                        lines.append(f"- {point}")
                    lines.append("")

                if debate_summary.safe_key_points:
                    lines.append(f"{self.SPEAKER_EMOJIS.get('Safe Analyst', '🛡️')} Safe Analyst")
                    for point in debate_summary.safe_key_points:
                        lines.append(f"- {point}")
                    lines.append("")

                if debate_summary.neutral_key_points:
                    lines.append(
                        f"{self.SPEAKER_EMOJIS.get('Neutral Analyst', '⚖️')} Neutral Analyst"
                    )
                    for point in debate_summary.neutral_key_points:
                        lines.append(f"- {point}")
                    lines.append("")

        # Level 3: Full transcript
        if level >= 3 and debate_summary.full_transcript:
            lines.append("## Full Transcript")
            lines.append("")
            lines.append("```")
            lines.append(debate_summary.full_transcript)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)
