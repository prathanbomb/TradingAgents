"""Debate parser for extracting structured arguments from debate state.

This module provides DebateParser for converting unstructured debate conversation
history from DecisionRecord.debate_state into structured Debate objects with
individual Argument instances extracted by speaker.
"""

import logging
import re
from typing import Dict, List, Literal, Optional

from pydantic import ValidationError

from tradingagents.observability.debate.models import Argument, Debate, Judgment
from tradingagents.observability.models.decision_record import DebateState

logger = logging.getLogger(__name__)


class DebateParser:
    """Parse debate state from DecisionRecord into structured debates.

    Extracts individual arguments from unstructured conversation history
    using speaker prefix patterns (e.g., "Bull Analyst: text").
    """

    # Default speaker patterns for different debate types
    DEFAULT_SPEAKER_PATTERNS: Dict[str, Dict[str, str]] = {
        "investment": {
            "bull": "Bull Analyst",
            "bear": "Bear Analyst",
            "judge": "Investment Judge",
        },
        "risk": {
            "risky": "Risky Analyst",
            "safe": "Safe Analyst",
            "neutral": "Neutral Analyst",
            "judge": "Risk Judge",
        },
    }

    def __init__(self, speaker_patterns: Optional[Dict[str, Dict[str, str]]] = None):
        """Initialize parser with optional custom speaker patterns.

        Args:
            speaker_patterns: Optional mapping of debate_type to speaker names.
                Defaults to standard patterns if not provided.
        """
        self.speaker_patterns = speaker_patterns or self.DEFAULT_SPEAKER_PATTERNS

    def parse_investment_debate(
        self,
        debate_state: DebateState,
        run_id: str,
        ticker: str,
        trade_date: str,
    ) -> Debate:
        """Parse bull/bear investment debate.

        Extracts arguments from bull_history and bear_history fields,
        identifies speaker prefixes ("Bull Analyst:", "Bear Analyst:"),
        and constructs a structured Debate object.

        Args:
            debate_state: InvestDebateState from DecisionRecord.debate_state
            run_id: Run identifier for linking to DecisionTrail
            ticker: Stock ticker symbol
            trade_date: Trade date in YYYY-MM-DD format

        Returns:
            Debate with bull and bear arguments + judgment
        """
        patterns = self.speaker_patterns.get("investment", self.DEFAULT_SPEAKER_PATTERNS["investment"])

        # Extract arguments from both speakers
        bull_args = self._parse_speaker_arguments(
            debate_state.bull_history,
            patterns["bull"],
            "investment"
        )
        bear_args = self._parse_speaker_arguments(
            debate_state.bear_history,
            patterns["bear"],
            "investment"
        )

        # Merge arguments preserving turn order
        all_arguments = self._merge_arguments_by_turn(bull_args, bear_args)

        # Validate argument count
        if debate_state.count > 0 and len(all_arguments) != debate_state.count:
            logger.warning(
                f"Argument count mismatch: expected {debate_state.count}, "
                f"extracted {len(all_arguments)} for investment debate {run_id}"
            )

        # Create judgment
        judgment = self._create_judgment(
            debate_state.judge_decision,
            patterns["judge"]
        )

        try:
            return Debate(
                debate_type="investment",
                run_id=run_id,
                ticker=ticker,
                trade_date=trade_date,
                arguments=all_arguments,
                judgment=judgment,
                total_turns=len(all_arguments),
            )
        except ValidationError as e:
            logger.error(f"Failed to create Debate: {e}")
            # Return empty debate on validation error
            return Debate(
                debate_type="investment",
                run_id=run_id,
                ticker=ticker,
                trade_date=trade_date,
                arguments=[],
                total_turns=0,
            )

    def parse_risk_debate(
        self,
        risk_debate_state: Dict,
        run_id: str,
        ticker: str,
        trade_date: str,
    ) -> Debate:
        """Parse three-way risk debate (risky/safe/neutral perspectives).

        Extracts arguments from risky_history, safe_history, and neutral_history,
        identifies three speaker prefixes ("Risky Analyst:", "Safe Analyst:", "Neutral Analyst:"),
        and constructs a structured Debate object.

        Args:
            risk_debate_state: RiskDebateState from DecisionRecord.debate_state
                (Dict with risky_history, safe_history, neutral_history, judge_decision)
            run_id: Run identifier for linking to DecisionTrail
            ticker: Stock ticker symbol
            trade_date: Trade date in YYYY-MM-DD format

        Returns:
            Debate with risky, safe, and neutral arguments + judgment
        """
        patterns = self.speaker_patterns.get("risk", self.DEFAULT_SPEAKER_PATTERNS["risk"])

        # Extract arguments from all three speakers
        risky_args = self._parse_speaker_arguments(
            risk_debate_state.get("risky_history", ""),
            patterns["risky"],
            "risk"
        )
        safe_args = self._parse_speaker_arguments(
            risk_debate_state.get("safe_history", ""),
            patterns["safe"],
            "risk"
        )
        neutral_args = self._parse_speaker_arguments(
            risk_debate_state.get("neutral_history", ""),
            patterns["neutral"],
            "risk"
        )

        # Merge arguments preserving turn order
        all_arguments = self._merge_arguments_by_turn(
            risky_args, safe_args, neutral_args
        )

        # Validate argument count
        count = risk_debate_state.get("count", 0)
        if count > 0 and len(all_arguments) != count:
            logger.warning(
                f"Argument count mismatch: expected {count}, "
                f"extracted {len(all_arguments)} for risk debate {run_id}"
            )

        # Create judgment
        judgment = self._create_judgment(
            risk_debate_state.get("judge_decision", ""),
            patterns["judge"]
        )

        try:
            return Debate(
                debate_type="risk",
                run_id=run_id,
                ticker=ticker,
                trade_date=trade_date,
                arguments=all_arguments,
                judgment=judgment,
                total_turns=len(all_arguments),
            )
        except ValidationError as e:
            logger.error(f"Failed to create Debate: {e}")
            # Return empty debate on validation error
            return Debate(
                debate_type="risk",
                run_id=run_id,
                ticker=ticker,
                trade_date=trade_date,
                arguments=[],
                total_turns=0,
            )

    def _parse_speaker_arguments(
        self,
        history: str,
        speaker: str,
        debate_type: Literal["investment", "risk"]
    ) -> List[Argument]:
        r"""Parse individual arguments from speaker's history.

        Uses regex pattern to identify argument boundaries:
        Pattern: r"Speaker:\s*(.*?)(?=\n(?:Speaker:)|\Z)"

        Handles edge cases:
        - Multi-line arguments (re.DOTALL flag)
        - Colons in argument text (negative lookahead)
        - Empty or malformed history (returns empty list)

        Args:
            history: Speaker's conversation history
            speaker: Speaker name to filter by
            debate_type: Type of debate for argument_type classification

        Returns:
            List of Argument objects in chronological order
        """
        if not history or not history.strip():
            return []

        # Escape speaker name for regex (handle special characters)
        escaped_speaker = re.escape(speaker)

        # Build pattern to match speaker-prefixed arguments
        # Pattern matches: "Speaker: text" up to next "Speaker:" or end of string
        # Uses negative lookahead to avoid capturing colons in argument text
        pattern = rf"{escaped_speaker}:\s*(.*?)(?=\n(?:{escaped_speaker}:)|\Z)"

        # Use DOTALL to capture multi-line arguments
        matches = re.findall(pattern, history, re.DOTALL)

        arguments = []
        for i, content in enumerate(matches, start=1):
            # Clean up whitespace
            content = content.strip()

            if not content:
                continue

            # Classify argument type heuristically
            arg_type = self._classify_argument_type(content)

            try:
                arg = Argument(
                    speaker=speaker,
                    content=content,
                    turn_number=i,
                    argument_type=arg_type,
                )
                arguments.append(arg)
            except ValidationError as e:
                logger.warning(f"Failed to create Argument for {speaker}: {e}")
                continue

        return arguments

    def _merge_arguments_by_turn(self, *arg_lists: List[Argument]) -> List[Argument]:
        """Merge argument lists from multiple speakers, sorting by turn_number.

        Args:
            *arg_lists: Variable number of Argument lists to merge

        Returns:
            Combined list of arguments sorted by turn_number
        """
        all_args = []
        for arg_list in arg_lists:
            all_args.extend(arg_list)

        # Sort by turn_number to maintain chronological order
        return sorted(all_args, key=lambda arg: arg.turn_number)

    def _create_judgment(
        self,
        judge_decision: str,
        judge_name: str
    ) -> Optional[Judgment]:
        """Create Judgment from judge decision text.

        Args:
            judge_decision: The judge's decision text
            judge_name: Name of the judge

        Returns:
            Judgment object, or None if decision text is empty
        """
        if not judge_decision or not judge_decision.strip():
            return None

        try:
            return Judgment(
                decision=judge_decision.strip(),
                judge=judge_name,
            )
        except ValidationError as e:
            logger.warning(f"Failed to create Judgment: {e}")
            return None

    def _classify_argument_type(
        self,
        content: str
    ) -> Literal["data_driven", "qualitative"]:
        """Classify argument type based on content heuristics.

        Args:
            content: Argument text content

        Returns:
            "data_driven" if content contains numbers/data, "qualitative" otherwise
        """
        # Check for numeric patterns (percentages, prices, ratios)
        numeric_pattern = r'\d+\.?\d*%|\$\d+\.?\d*|\d+\.\d+'

        if re.search(numeric_pattern, content):
            return "data_driven"

        return "qualitative"
