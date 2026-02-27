"""Judgment visualization for debate resolution analysis.

This module provides JudgmentVisualizer for extracting judgment reasoning,
identifying winning arguments, and linking debate outcomes to trading decisions.
"""

import logging
import re
from typing import Dict, List, Literal, Optional

from tradingagents.observability.debate.models import (
    Argument,
    Debate,
    Judgment,
    JudgmentView,
    DecisionInfluence,
)
from tradingagents.backtracking.agent_tracker import TradingSignal

logger = logging.getLogger(__name__)


class JudgmentVisualizer:
    """Visualize how debates were resolved and influenced decisions.

    Extracts judgment reasoning, identifies winning arguments, and links
    debate outcomes to final trading decisions.
    """

    def __init__(self, explorer=None):
        """Initialize visualizer with debate explorer.

        Args:
            explorer: DebateExplorer for retrieving debates (optional, for future use)
        """
        self.explorer = explorer

        # Patterns for identifying winners from judgment text
        self.winner_patterns = {
            "investment": {
                "bull": r"\bbull\b|\bbullish\b|\bbuy\b|\blong\b",
                "bear": r"\bbear\b|\bbearish\b|\bsell\b|\bshort\b",
            },
            "risk": {
                "risky": r"\brisky\b|\brisk\b|\baggressive\b",
                "safe": r"\bsafe\b|\bconservative\b|\bcautious\b",
                "neutral": r"\bneutral\b|\bbalanced\b|\bmoderate\b",
            },
        }

        # Ambiguous judgment patterns
        self.ambiguous_patterns = [
            r"too close to call",
            r"mixed signals?",
            r"unclear",
            r"inconclusive",
            r"no clear winner",
            r"insufficient data",
        ]

    def visualize_judgment(
        self,
        debate: Debate,
        level: Literal[1, 2, 3] = 1
    ) -> JudgmentView:
        """Create structured view of debate resolution.

        Analyzes judgment text to identify which side won (bull/bear
        or risky/safe/neutral) and extracts reasoning.

        Args:
            debate: Debate object with judgment populated
            level: Disclosure level (1: summary, 2: key arguments, 3: full details)

        Returns:
            JudgmentView with structured resolution data
        """
        if not debate.judgment:
            logger.warning(f"Debate {debate.debate_id} has no judgment")
            return self._create_unknown_judgment_view(debate)

        judgment = debate.judgment

        # Identify winner from judgment text
        winner = self._identify_winner(debate)
        winner_summary = self._extract_winner_summary(judgment.decision, winner)

        # Create judgment summary (truncated)
        judgment_summary = self._truncate_text(judgment.decision, 200)

        # Build base view (Level 1)
        view_data = {
            "debate_id": debate.debate_id,
            "winner": winner,
            "winner_summary": winner_summary,
            "judgment_summary": judgment_summary,
            "timestamp": judgment.timestamp,
        }

        # Level 2: Add key arguments and reasoning
        if level >= 2:
            winning_arguments = self.identify_winning_arguments(debate)
            losing_arguments = self._identify_losing_arguments(debate, winner)
            judgment_reasoning = self.extract_judgment_reasoning(judgment)

            view_data.update({
                "winning_arguments": [arg.content for arg in winning_arguments],
                "losing_arguments": losing_arguments,
                "judgment_reasoning": judgment_reasoning,
            })

        # Level 3: Add full details
        if level >= 3:
            all_arguments_by_speaker: Dict[str, List[str]] = self._group_arguments_by_speaker(debate)

            view_data.update({
                "full_judgment": judgment.decision,
                "all_arguments": all_arguments_by_speaker,
            })

        try:
            return JudgmentView(**view_data)
        except Exception as e:
            logger.error(f"Failed to create JudgmentView: {e}")
            return self._create_unknown_judgment_view(debate)

    def extract_judgment_reasoning(self, judgment: Judgment) -> str:
        """Extract judge's reasoning from decision text.

        Parses judge_decision to identify why the judge chose the winner.
        Looks for reasoning indicators: "because", "due to", "given that".

        Args:
            judgment: Judgment object from Debate

        Returns:
            Extracted reasoning string (or original decision if no reasoning found)
        """
        decision = judgment.decision

        # Look for reasoning patterns
        reasoning_patterns = [
            r"(?:because|due to|given that|as|since)\s+([^,.]+[.,]?)",
            r"(?:reason|rationale|justification):\s*([^,.]+[.,]?)",
            r"(?:based on|considering)\s+([^,.]+[.,]?)",
        ]

        for pattern in reasoning_patterns:
            match = re.search(pattern, decision, re.IGNORECASE)
            if match:
                reasoning = match.group(1).strip()
                if len(reasoning) > 20:  # Ensure it's substantial
                    return self._truncate_text(reasoning, 200)

        # No explicit reasoning found, return original decision truncated
        return self._truncate_text(decision, 200)

    def identify_winning_arguments(
        self,
        debate: Debate
    ) -> List[Argument]:
        """Identify arguments that align with winning judgment.

        Uses keyword matching between judgment text and argument content
        to identify which arguments the judge found persuasive.

        Args:
            debate: Debate with judgment and arguments

        Returns:
            List of Argument objects that align with judgment
        """
        if not debate.judgment:
            return []

        judgment_text = debate.judgment.decision.lower()
        winner = self._identify_winner(debate)

        # Get arguments from winner
        winner_arguments = [
            arg for arg in debate.arguments
            if arg.speaker == winner
        ]

        # Extract keywords from judgment
        keywords = self._extract_keywords(judgment_text)

        # Score arguments by keyword overlap
        scored_arguments = []
        for arg in winner_arguments:
            score = self._calculate_keyword_overlap(arg.content.lower(), keywords)
            if score > 0:
                scored_arguments.append((arg, score))

        # Sort by score and return top arguments
        scored_arguments.sort(key=lambda x: x[1], reverse=True)
        return [arg for arg, _ in scored_arguments]

    def link_judgment_to_decision(
        self,
        debate: Debate,
        decision_record
    ) -> DecisionInfluence:
        """Analyze how debate influenced final trading decision.

        Compares judgment outcome (bull wins / bear wins) with final_signal
        to measure debate influence on decision.

        Args:
            debate: Debate with judgment
            decision_record: DecisionRecord from same run_id

        Returns:
            DecisionInfluence with alignment and influence score
        """
        if not debate.judgment:
            return self._create_neutral_influence(debate, decision_record, "No judgment available")

        judgment_winner = self._identify_winner(debate)
        final_decision = decision_record.final_signal.value

        # Determine alignment
        alignment = self._determine_alignment(judgment_winner, final_decision, debate.debate_type)

        # Calculate influence score
        influence_score = self._calculate_influence_score(
            judgment_winner, final_decision, alignment, debate.debate_type
        )

        # Generate reasoning
        reasoning = self._generate_influence_reasoning(
            judgment_winner, final_decision, alignment, debate.debate_type
        )

        return DecisionInfluence(
            debate_id=debate.debate_id,
            decision_id=decision_record.decision_id,
            judgment_winner=judgment_winner,
            final_decision=final_decision,
            alignment=alignment,
            influence_score=influence_score,
            reasoning=reasoning,
        )

    def _identify_winner(self, debate: Debate) -> str:
        """Identify winner from judgment text.

        Args:
            debate: Debate with judgment

        Returns:
            Winner speaker name or "Inconclusive" if ambiguous
        """
        if not debate.judgment:
            return "Unknown"

        decision_text = debate.judgment.decision.lower()

        # Check for ambiguous judgments
        for pattern in self.ambiguous_patterns:
            if re.search(pattern, decision_text, re.IGNORECASE):
                return "Inconclusive"

        # Get patterns for debate type
        patterns = self.winner_patterns.get(debate.debate_type, {})

        # Count keyword matches for each side
        scores = {}
        for side, pattern in patterns.items():
            matches = len(re.findall(pattern, decision_text, re.IGNORECASE))
            scores[side] = matches

        # Determine winner by highest score
        if not scores or max(scores.values()) == 0:
            return "Inconclusive"

        winner_side = max(scores, key=scores.get)

        # Map side to speaker name
        speaker_mapping = {
            "bull": "Bull Analyst",
            "bear": "Bear Analyst",
            "risky": "Risky Analyst",
            "safe": "Safe Analyst",
            "neutral": "Neutral Analyst",
        }

        return speaker_mapping.get(winner_side, winner_side.capitalize())

    def _extract_winner_summary(self, judgment_decision: str, winner: str) -> str:
        """Extract 1-sentence summary of why winner won.

        Args:
            judgment_decision: Full judgment decision text
            winner: Winner speaker name

        Returns:
            1-sentence summary
        """
        # Try to extract a sentence containing reasoning
        sentences = re.split(r'[.!?]', judgment_decision)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 150:
                # Check if sentence contains reasoning indicators
                if any(indicator in sentence.lower() for indicator in ['because', 'due to', 'given', 'based']):
                    return sentence

        # Fallback: return first sentence truncated
        first_sentence = sentences[0].strip() if sentences else judgment_decision
        return self._truncate_text(first_sentence, 200)

    def _identify_losing_arguments(self, debate: Debate, winner: str) -> List[str]:
        """Identify arguments from losing side.

        Args:
            debate: Debate with arguments
            winner: Winner speaker name

        Returns:
            List of losing argument content strings
        """
        # Determine losing side based on winner
        loser_mapping = {
            "Bull Analyst": "Bear Analyst",
            "Bear Analyst": "Bull Analyst",
            "Risky Analyst": "Safe Analyst",
            "Safe Analyst": "Risky Analyst",
            "Neutral Analyst": "Inconclusive",
        }

        loser = loser_mapping.get(winner)

        if not loser:
            return []

        # Return arguments from loser (limited to 3)
        losing_args = [
            arg.content for arg in debate.arguments
            if arg.speaker == loser
        ][:3]

        return losing_args

    def _group_arguments_by_speaker(self, debate: Debate) -> dict:
        """Group all arguments by speaker.

        Args:
            debate: Debate with arguments

        Returns:
            Dictionary mapping speaker names to their argument contents
        """
        speaker_args = {}
        for arg in debate.arguments:
            if arg.speaker not in speaker_args:
                speaker_args[arg.speaker] = []
            speaker_args[arg.speaker].append(arg.content)

        return speaker_args

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            List of keywords
        """
        # Simple keyword extraction: words longer than 4 chars
        words = re.findall(r'\b[a-z]{4,}\b', text)
        # Remove common words
        stop_words = {'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they', 'their', 'there'}
        keywords = [w for w in words if w not in stop_words]
        return keywords

    def _calculate_keyword_overlap(self, text: str, keywords: List[str]) -> int:
        """Calculate keyword overlap score.

        Args:
            text: Text to check
            keywords: Keywords to look for

        Returns:
            Number of keyword matches
        """
        score = 0
        for keyword in keywords:
            if keyword in text:
                score += 1
        return score

    def _determine_alignment(
        self,
        judgment_winner: str,
        final_decision: str,
        debate_type: str
    ) -> Literal["aligned", "opposed", "neutral"]:
        """Determine alignment between judgment and decision.

        Args:
            judgment_winner: Winner speaker name
            final_decision: Final trading signal
            debate_type: Type of debate

        Returns:
            Alignment type
        """
        if debate_type == "investment":
            if judgment_winner == "Bull Analyst" and final_decision == "BUY":
                return "aligned"
            elif judgment_winner == "Bear Analyst" and final_decision == "SELL":
                return "aligned"
            elif judgment_winner == "Bull Analyst" and final_decision == "SELL":
                return "opposed"
            elif judgment_winner == "Bear Analyst" and final_decision == "BUY":
                return "opposed"
            else:
                return "neutral"
        else:  # risk debate
            if judgment_winner == "Risky Analyst" and final_decision in ["BUY", "SELL"]:
                return "aligned"  # Risky supports active trading
            elif judgment_winner == "Safe Analyst" and final_decision == "HOLD":
                return "aligned"
            elif judgment_winner == "Neutral Analyst":
                return "neutral"
            else:
                return "neutral"

    def _calculate_influence_score(
        self,
        judgment_winner: str,
        final_decision: str,
        alignment: Literal["aligned", "opposed", "neutral"],
        debate_type: str
    ) -> float:
        """Calculate influence score (0.0-1.0).

        Args:
            judgment_winner: Winner speaker name
            final_decision: Final trading signal
            alignment: Alignment type
            debate_type: Type of debate

        Returns:
            Influence score
        """
        if alignment == "aligned":
            return 0.85  # High influence when aligned
        elif alignment == "opposed":
            return 0.15  # Low influence when opposed
        else:
            return 0.50  # Neutral influence

    def _generate_influence_reasoning(
        self,
        judgment_winner: str,
        final_decision: str,
        alignment: Literal["aligned", "opposed", "neutral"],
        debate_type: str
    ) -> str:
        """Generate human-readable reasoning for influence.

        Args:
            judgment_winner: Winner speaker name
            final_decision: Final trading signal
            alignment: Alignment type
            debate_type: Type of debate

        Returns:
            Human-readable reasoning
        """
        if alignment == "aligned":
            return f"{judgment_winner} won the debate and final decision is {final_decision} (aligned)"
        elif alignment == "opposed":
            return f"{judgment_winner} won the debate but final decision is {final_decision} (opposed)"
        else:
            return f"{judgment_winner} won the debate but decision is {final_decision} (neutral alignment)"

    def _create_unknown_judgment_view(self, debate: Debate) -> JudgmentView:
        """Create JudgmentView for unknown/missing judgment.

        Args:
            debate: Debate without judgment

        Returns:
            JudgmentView with unknown status
        """
        return JudgmentView(
            debate_id=debate.debate_id,
            winner="Unknown",
            winner_summary="No judgment available",
            judgment_summary="No judgment provided for this debate",
        )

    def _create_neutral_influence(
        self,
        debate: Debate,
        decision_record,
        reason: str
    ) -> DecisionInfluence:
        """Create neutral DecisionInfluence.

        Args:
            debate: Debate object
            decision_record: DecisionRecord object
            reason: Reason for neutral influence

        Returns:
            DecisionInfluence with neutral alignment
        """
        return DecisionInfluence(
            debate_id=debate.debate_id,
            decision_id=decision_record.decision_id,
            judgment_winner="Unknown",
            final_decision=decision_record.final_signal.value,
            alignment="neutral",
            influence_score=0.0,
            reasoning=reason,
        )


class JudgmentRenderer:
    """Render judgment visualizations for display.

    Provides text-based rendering of JudgmentView and DecisionInfluence
    with formatting consistent with DebateRenderer and TrailRenderer.
    """

    def render_judgment_view(
        self,
        judgment_view: JudgmentView,
        level: Literal[1, 2, 3] = 1
    ) -> str:
        """Render judgment at specified disclosure level.

        Level 1: Winner + summary
        Level 2: Winner + summary + key arguments
        Level 3: Winner + summary + key arguments + full judgment

        Args:
            judgment_view: JudgmentView to render
            level: Disclosure level (1-3)

        Returns:
            Formatted text representation of judgment
        """
        lines = []

        # Winner emoji mapping
        emoji_map = {
            "Bull Analyst": "🐂",
            "Bear Analyst": "🐻",
            "Risky Analyst": "⚠️",
            "Safe Analyst": "🛡️",
            "Neutral Analyst": "⚖️",
            "Inconclusive": "❓",
            "Unknown": "❓",
        }

        emoji = emoji_map.get(judgment_view.winner, "")

        # Level 1: Winner + summary
        lines.append(f"## Judgment Resolution {emoji}")
        lines.append(f"**Winner:** {judgment_view.winner}")
        lines.append(f"**Summary:** {judgment_view.winner_summary}")
        lines.append("")

        # Level 2: Key arguments
        if level >= 2 and judgment_view.winning_arguments:
            lines.append("### Winning Arguments")
            for i, arg in enumerate(judgment_view.winning_arguments, 1):
                truncated = self._truncate_text(arg, 150)
                lines.append(f"  {i}. {truncated}")
            lines.append("")

        if level >= 2 and judgment_view.judgment_reasoning:
            lines.append(f"**Reasoning:** {judgment_view.judgment_reasoning}")
            lines.append("")

        # Level 3: Full judgment
        if level >= 3 and judgment_view.full_judgment:
            lines.append("### Full Judgment")
            lines.append(judgment_view.full_judgment)
            lines.append("")

        return "\n".join(lines)

    def render_decision_influence(
        self,
        influence: DecisionInfluence
    ) -> str:
        """Render how debate influenced trading decision.

        Shows alignment, influence score, and reasoning.

        Args:
            influence: DecisionInfluence to render

        Returns:
            Formatted text representation of influence
        """
        lines = []

        # Alignment emoji
        alignment_emoji = {
            "aligned": "✅",
            "opposed": "⚠️",
            "neutral": "➖",
        }

        emoji = alignment_emoji.get(influence.alignment, "")

        lines.append(f"## Decision Influence {emoji}")
        lines.append(f"**Judgment Winner:** {influence.judgment_winner}")
        lines.append(f"**Final Decision:** {influence.final_decision}")
        lines.append(f"**Alignment:** {influence.alignment.upper()}")
        lines.append(f"**Influence Score:** {influence.influence_score * 100:.0f}%")
        lines.append(f"**Reasoning:** {influence.reasoning}")
        lines.append("")

        return "\n".join(lines)

    def render_judgment_timeline(
        self,
        debate: Debate,
        judgment_view: JudgmentView
    ) -> str:
        """Render debate timeline with judgment highlighted.

        Shows all arguments in chronological order, with winning
        arguments marked (e.g., ✓, ★) to show what the judge found persuasive.

        Args:
            debate: Full Debate object
            judgment_view: JudgmentView with winning arguments

        Returns:
            Formatted timeline with judgment highlights
        """
        lines = []

        lines.append(f"## Debate Timeline: {debate.ticker} ({debate.trade_date})")
        lines.append("")

        # Get winning argument IDs for marking
        winning_contents = set()
        if judgment_view.winning_arguments:
            winning_contents = set(judgment_view.winning_arguments)

        # Render arguments in order
        for arg in debate.arguments:
            # Check if this is a winning argument
            is_winning = arg.content in winning_contents
            marker = "✓" if is_winning else " "

            lines.append(f"{marker} **Turn {arg.turn_number}** - {arg.speaker}")
            # Truncate argument content for display
            truncated = self._truncate_text(arg.content, 200)
            lines.append(f"  {truncated}")
            lines.append("")

        # Add judgment at the end
        if debate.judgment:
            lines.append("### ⚖️ Judgment")
            lines.append(f"**{debate.judgment.judge}:** {debate.judgment.decision}")
            lines.append("")

        return "\n".join(lines)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
