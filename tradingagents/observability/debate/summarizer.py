"""Debate summarizer for extracting key points from debate transcripts.

This module provides DebateSummarizer for generating 3-level progressive
disclosure summaries (summary → key points → full transcript) using
LLM-based summarization with extractive fallback.
"""

import json
import logging
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from tradingagents.observability.debate.models import Debate

logger = logging.getLogger(__name__)


class DebateSummarizer:
    """Extract key points from debate transcripts for progressive disclosure.

    Uses LLM-based summarization (GPT-3.5-turbo) with extractive fallback (sumy)
    to generate 3-level disclosure: summary → key points → full transcript.
    """

    # Default LLM configuration
    DEFAULT_MODEL = "gpt-3.5-turbo"
    DEFAULT_TEMPERATURE = 0

    # Default summary constraints
    DEFAULT_MAX_POINTS_PER_SPEAKER = 5
    SUMMARY_MAX_LENGTH = 280

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        use_extractive_fallback: bool = True,
        cache_dir: Optional[str] = None,
    ):
        """Initialize summarizer with LLM and fallback configuration.

        Args:
            llm: LangChain ChatOpenAI instance (default: gpt-3.5-turbo, temp=0)
            use_extractive_fallback: If True, use sumy when LLM unavailable
            cache_dir: Optional directory for caching summaries (default: None)

        Note:
            If no LLM is provided and OPENAI_API_KEY is not set, the summarizer
            will operate in fallback-only mode (using extractive summarization).
        """
        if llm is None:
            try:
                self.llm = ChatOpenAI(
                    model=self.DEFAULT_MODEL,
                    temperature=self.DEFAULT_TEMPERATURE,
                )
            except Exception as e:
                logger.warning(f"Could not initialize LLM: {e}. Falling back to extractive-only mode.")
                self.llm = None
        else:
            self.llm = llm

        self.use_extractive_fallback = use_extractive_fallback
        self.cache_dir = cache_dir

        # In-memory cache for summaries (cache_dir=None case)
        self._cache: Dict[str, any] = {}

        # Build prompt templates
        self._key_points_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert at analyzing trading debates. "
                "Extract the 3-5 most important arguments from each speaker. "
                "Focus on specific data points, risks, and opportunities."
            )),
            ("human", (
                "Debate Type: {debate_type}\n"
                "Ticker: {ticker}\n\n"
                "Transcript:\n{transcript}\n\n"
                "Extract 3-5 key points per speaker. Return as JSON:\n"
                "{{\n"
                '  "speaker_name": ["key point 1", "key point 2", ...],\n'
                "  ...\n"
                "}}"
            )),
        ])

        self._debate_summary_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert at summarizing trading debates. "
                "Create a 1-2 sentence summary that captures the core conflict "
                "and resolution."
            )),
            ("human", (
                "Debate Type: {debate_type}\n"
                "Ticker: {ticker}\n\n"
                "Arguments:\n{arguments_summary}\n\n"
                "Judgment: {judgment}\n\n"
                "Provide a 1-2 sentence summary."
            )),
        ])

    def summarize_debate(self, debate: Debate) -> "DebateSummary":
        """Generate 3-level summary for progressive disclosure.

        Args:
            debate: Parsed Debate object from DebateParser

        Returns:
            DebateSummary with summary, key_points, and full_transcript
        """
        from tradingagents.observability.debate.models import DebateSummary

        # Check cache first
        if debate.debate_id in self._cache:
            logger.debug(f"Using cached summary for debate {debate.debate_id}")
            return self._cache[debate.debate_id]

        # Handle empty debate
        if not debate.arguments:
            logger.warning(f"Empty debate {debate.debate_id}, returning minimal summary")
            return DebateSummary(
                debate_id=debate.debate_id,
                debate_type=debate.debate_type,
                summary="No debate data available",
                judgment_summary=debate.judgment.decision if debate.judgment else "",
                total_turns=0,
                total_arguments=0,
                llm_model=self.llm.model_name,
            )

        try:
            # Generate summary
            summary = self.generate_debate_summary(debate)

            # Extract key points
            key_points = self.extract_key_points(debate)

            # Build full transcript
            full_transcript = self._build_full_transcript(debate)

            # Map key points to speakers based on debate type
            summary_data = {
                "debate_id": debate.debate_id,
                "debate_type": debate.debate_type,
                "summary": summary,
                "judgment_summary": debate.judgment.decision if debate.judgment else "",
                "total_turns": debate.total_turns,
                "total_arguments": len(debate.arguments),
                "full_transcript": full_transcript,
                "llm_model": self.llm.model_name,
            }

            # Add speaker-specific key points
            if debate.debate_type == "investment":
                summary_data["bull_key_points"] = key_points.get("Bull Analyst", [])
                summary_data["bear_key_points"] = key_points.get("Bear Analyst", [])
            elif debate.debate_type == "risk":
                summary_data["risky_key_points"] = key_points.get("Risky Analyst", [])
                summary_data["safe_key_points"] = key_points.get("Safe Analyst", [])
                summary_data["neutral_key_points"] = key_points.get("Neutral Analyst", [])

            # Create DebateSummary
            debate_summary = DebateSummary(**summary_data)

            # Cache the result
            self._cache[debate.debate_id] = debate_summary

            return debate_summary

        except Exception as e:
            logger.error(f"Failed to summarize debate {debate.debate_id}: {e}")
            # Return minimal summary on error
            return DebateSummary(
                debate_id=debate.debate_id,
                debate_type=debate.debate_type,
                summary="Summary unavailable due to error",
                judgment_summary=debate.judgment.decision if debate.judgment else "",
                total_turns=debate.total_turns,
                total_arguments=len(debate.arguments),
            )

    def extract_key_points(
        self,
        debate: Debate,
        max_points_per_speaker: int = 5
    ) -> Dict[str, List[str]]:
        """Extract 3-5 key points per speaker using LLM.

        Builds transcript from all arguments, prompts LLM to identify
        the most important arguments (data points, risks, opportunities).

        Args:
            debate: Parsed Debate object
            max_points_per_speaker: Maximum key points to extract per speaker

        Returns:
            Dict mapping speaker names to lists of key points
        """
        # If no LLM available, use extractive fallback immediately
        if self.llm is None:
            logger.info("LLM not available, using extractive fallback for key points")
            if self.use_extractive_fallback:
                return self._extractive_summarize(debate, max_points_per_speaker)
            return {}

        # Build transcript for LLM
        transcript = self._build_transcript_for_llm(debate)

        try:
            # Invoke LLM
            chain = self._key_points_prompt | self.llm
            response = chain.invoke({
                "debate_type": debate.debate_type,
                "ticker": debate.ticker,
                "transcript": transcript,
            })

            # Parse JSON response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            key_points = json.loads(content.strip())

            # Limit to max_points_per_speaker
            for speaker in key_points:
                if len(key_points[speaker]) > max_points_per_speaker:
                    key_points[speaker] = key_points[speaker][:max_points_per_speaker]

            return key_points

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"LLM key point extraction failed: {e}. Using extractive fallback.")
            if self.use_extractive_fallback:
                return self._extractive_summarize(debate, max_points_per_speaker)
            return {}

    def generate_debate_summary(self, debate: Debate) -> str:
        """Generate 1-2 sentence summary of entire debate.

        Captures the core conflict and resolution: e.g.,
        "Bull argues strong earnings growth while Bear highlights
        valuation concerns. Judge favors Bull due to momentum."

        Args:
            debate: Parsed Debate object

        Returns:
            1-2 sentence summary string
        """
        judgment_text = debate.judgment.decision if debate.judgment else "No judgment"

        # If no LLM available, use simple fallback immediately
        if self.llm is None:
            logger.info("LLM not available, using fallback for debate summary")
            speaker_names = list(set(arg.speaker for arg in debate.arguments))
            if len(speaker_names) == 2:
                return f"Debate between {speaker_names[0]} and {speaker_names[1]}. {judgment_text}"
            else:
                return f"Multi-perspective debate. {judgment_text}"

        # Build arguments summary
        arguments_summary = self._build_arguments_summary(debate)

        try:
            # Invoke LLM
            chain = self._debate_summary_prompt | self.llm
            response = chain.invoke({
                "debate_type": debate.debate_type,
                "ticker": debate.ticker,
                "arguments_summary": arguments_summary,
                "judgment": judgment_text,
            })

            summary = response.content.strip()

            # Truncate to max length
            if len(summary) > self.SUMMARY_MAX_LENGTH:
                summary = summary[:self.SUMMARY_MAX_LENGTH - 3] + "..."

            return summary

        except Exception as e:
            logger.warning(f"LLM debate summary failed: {e}. Using fallback.")
            # Fallback to simple summary
            speaker_names = list(set(arg.speaker for arg in debate.arguments))
            if len(speaker_names) == 2:
                return f"Debate between {speaker_names[0]} and {speaker_names[1]}. {judgment_text}"
            else:
                return f"Multi-perspective debate. {judgment_text}"

    def _extractive_summarize(
        self,
        debate: Debate,
        max_points_per_speaker: int = 5
    ) -> Dict[str, List[str]]:
        """Extract key points using extractive summarization (fallback).

        Uses sumy's LexRank algorithm to identify the most important
        sentences from each speaker's arguments.

        Args:
            debate: Parsed Debate object
            max_points_per_speaker: Maximum key points to extract per speaker

        Returns:
            Dict mapping speaker names to lists of key points
        """
        try:
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.summarizers.lex_rank import LexRankSummarizer
            from sumy.nlp.tokenizers import Tokenizer
        except ImportError:
            logger.warning("sumy not installed. Extractive fallback unavailable.")
            return {}

        key_points = {}

        # Group arguments by speaker
        for speaker in set(arg.speaker for arg in debate.arguments):
            speaker_args = [arg for arg in debate.arguments if arg.speaker == speaker]

            # Build text from speaker's arguments
            text = "\n".join(arg.content for arg in speaker_args)

            try:
                # Parse and summarize
                parser = PlaintextParser.from_string(text, Tokenizer("english"))
                summarizer = LexRankSummarizer()

                # Extract top N sentences as key points
                sentences = summarizer(
                    parser.document,
                    sentences_count=min(max_points_per_speaker, len(speaker_args))
                )

                key_points[speaker] = [str(sentence) for sentence in sentences]

            except Exception as e:
                logger.warning(f"Extractive summarization failed for {speaker}: {e}")
                key_points[speaker] = []

        return key_points

    def _build_transcript_for_llm(self, debate: Debate) -> str:
        """Build formatted transcript for LLM consumption.

        Args:
            debate: Parsed Debate object

        Returns:
            Formatted transcript string
        """
        lines = []
        for arg in debate.arguments:
            lines.append(f"{arg.speaker}: {arg.content}")
        return "\n\n".join(lines)

    def _build_arguments_summary(self, debate: Debate) -> str:
        """Build summary of arguments for LLM.

        Args:
            debate: Parsed Debate object

        Returns:
            Summary string
        """
        # Count arguments per speaker
        speaker_counts = {}
        for arg in debate.arguments:
            speaker_counts[arg.speaker] = speaker_counts.get(arg.speaker, 0) + 1

        parts = []
        for speaker, count in speaker_counts.items():
            parts.append(f"{speaker}: {count} arguments")

        return ", ".join(parts)

    def _build_full_transcript(self, debate: Debate) -> str:
        """Build full transcript for Level 3 disclosure.

        Args:
            debate: Parsed Debate object

        Returns:
            Full transcript string
        """
        lines = [f"Debate: {debate.ticker} ({debate.debate_type})"]
        lines.append(f"Date: {debate.trade_date}")
        lines.append("")

        for arg in debate.arguments:
            lines.append(f"Turn {arg.turn_number} - {arg.speaker}:")
            lines.append(arg.content)
            lines.append("")

        if debate.judgment:
            lines.append(f"Judgment ({debate.judgment.judge}):")
            lines.append(debate.judgment.decision)
            if debate.judgment.reasoning:
                lines.append(f"Reasoning: {debate.judgment.reasoning}")

        return "\n".join(lines)
