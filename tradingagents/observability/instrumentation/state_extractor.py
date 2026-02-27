"""State extractor for parsing AgentState into DecisionRecord objects.

This module provides StateExtractor for converting the nested AgentState
structure into structured DecisionRecord objects with proper signal extraction.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.backtracking.agent_tracker import TradingSignal

from tradingagents.observability.confidence import ConfidenceAggregator, ConfidenceScorer
from tradingagents.observability.models import DecisionRecord, DebateState

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Structured JSON logger for observability events.

    Provides structured logging with consistent formatting for all
    observability events, making logs queryable and machine-readable.
    """

    @staticmethod
    def _format_log(record: logging.LogRecord) -> str:
        """Format log record as structured JSON.

        Args:
            record: Python logging LogRecord

        Returns:
            JSON-formatted log string
        """
        log_dict = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra context if present
        if hasattr(record, "agent"):
            log_dict["agent"] = record.agent
        if hasattr(record, "ticker"):
            log_dict["ticker"] = record.ticker
        if hasattr(record, "trade_date"):
            log_dict["trade_date"] = record.trade_date
        if hasattr(record, "decision"):
            log_dict["decision"] = record.decision
        if hasattr(record, "run_id"):
            log_dict["run_id"] = record.run_id

        return json.dumps(log_dict)

    @classmethod
    def setup_handler(cls, logger_instance: logging.Logger):
        """Configure structured JSON handler for logger.

        Args:
            logger_instance: Logger instance to configure
        """
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))

        class JSONFilter(logging.Filter):
            def filter(self, record):
                record.msg = cls._format_log(record)
                return True

        handler.addFilter(JSONFilter())
        logger_instance.addHandler(handler)


# Set up structured logging for this module
StructuredLogger.setup_handler(logger)


class StateExtractor:
    """Extracts decision records from AgentState.

    Converts the nested AgentState structure into DecisionRecord models
    with proper signal extraction and debate capture.

    Example:
        ```python
        extractor = StateExtractor()
        records = extractor.extract_decision_records(
            final_state=agent_state,
            ticker="AAPL",
            trade_date="2026-02-27"
        )
        # Returns list of DecisionRecord objects for each agent
        ```
    """

    def __init__(
        self,
        confidence_scorer: Optional[ConfidenceScorer] = None,
        aggregator: Optional[ConfidenceAggregator] = None,
    ):
        """Initialize the state extractor.

        Args:
            confidence_scorer: Optional ConfidenceScorer for extracting confidence
                from agent reasoning. Defaults to None (creates new scorer).
            aggregator: Optional ConfidenceAggregator for computing system-level
                confidence from individual agent confidences. Defaults to Bayesian.
        """
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        self.aggregator = aggregator or ConfidenceAggregator(method="bayesian")
        logger.debug(
            "Initialized StateExtractor with confidence scoring "
            f"and {self.aggregator.method} aggregation"
        )

    def extract_decision_records(
        self,
        final_state: Dict[str, Any],
        ticker: str,
        trade_date: str,
        run_id: Optional[str] = None,
    ) -> List[DecisionRecord]:
        """Extract all decision records from final AgentState.

        Args:
            final_state: Final state from graph.propagate()
            ticker: Stock ticker symbol
            trade_date: Trade date (YYYY-MM-DD)
            run_id: Optional run identifier for grouping events

        Returns:
            List of DecisionRecord objects, one per agent that made a decision
        """
        records = []

        logger.debug(
            f"Extracting decisions for {ticker} on {trade_date}",
            extra={
                "ticker": ticker,
                "trade_date": trade_date,
                "run_id": run_id,
            }
        )

        # Extract analyst decisions
        records.extend(
            self._extract_analyst_decisions(final_state, ticker, trade_date, run_id)
        )

        # Extract researcher decisions
        records.extend(
            self._extract_researcher_decisions(final_state, ticker, trade_date, run_id)
        )

        # Extract trader decision
        trader_record = self._extract_trader_decision(
            final_state, ticker, trade_date, run_id
        )
        if trader_record:
            records.append(trader_record)

        # Extract risk judge decision
        risk_record = self._extract_risk_decision(
            final_state, ticker, trade_date, run_id
        )
        if risk_record:
            records.append(risk_record)

        # Extract final decision
        final_record = self._extract_final_decision(
            final_state, ticker, trade_date, run_id
        )
        if final_record:
            records.append(final_record)

        # Compute system-level confidence for final decision record
        self._compute_system_confidence(records)

        logger.info(
            f"Extracted {len(records)} decision records",
            extra={
                "ticker": ticker,
                "trade_date": trade_date,
                "run_id": run_id,
                "record_count": len(records),
            }
        )
        return records

    def _extract_analyst_decisions(
        self,
        final_state: Dict[str, Any],
        ticker: str,
        trade_date: str,
        run_id: Optional[str],
    ) -> List[DecisionRecord]:
        """Extract decisions from analyst reports.

        Args:
            final_state: Final AgentState
            ticker: Stock ticker
            trade_date: Trade date
            run_id: Run identifier

        Returns:
            List of DecisionRecord objects for each analyst
        """
        records = []
        analysts = [
            ("market_report", "Market Analyst", "market"),
            ("sentiment_report", "Social Media Analyst", "sentiment"),
            ("news_report", "News Researcher", "news"),
            ("fundamentals_report", "Fundamentals Researcher", "fundamentals"),
        ]

        for field, agent_name, agent_key in analysts:
            report = final_state.get(field, "")
            if report:
                signal = self._extract_signal(report)
                # Extract confidence from reasoning
                confidence = self._extract_confidence_for_testing(report)
                decision_record = DecisionRecord(
                    ticker=ticker,
                    trade_date=trade_date,
                    run_id=run_id,
                    agent_name=agent_name,
                    agent_type="analyst",
                    decision=signal.value,
                    reasoning=report[:1000] if len(report) > 1000 else report,  # Truncate long reports
                    final_signal=signal,
                    confidence=confidence,
                )
                records.append(decision_record)

                # Log individual analyst decision
                logger.debug(
                    f"Extracted analyst decision from {agent_name}",
                    extra={
                        "agent": agent_name,
                        "agent_type": "analyst",
                        "ticker": ticker,
                        "trade_date": trade_date,
                        "decision": signal.value,
                        "run_id": run_id,
                    }
                )

        return records

    def _extract_researcher_decisions(
        self,
        final_state: Dict[str, Any],
        ticker: str,
        trade_date: str,
        run_id: Optional[str],
    ) -> List[DecisionRecord]:
        """Extract decisions from investment debate state.

        Args:
            final_state: Final AgentState
            ticker: Stock ticker
            trade_date: Trade date
            run_id: Run identifier

        Returns:
            List of DecisionRecord objects for bull/bear researchers and judge
        """
        records = []
        debate_state = final_state.get("investment_debate_state", {})

        if not debate_state:
            return records

        # Extract bull researcher position
        bull_history = debate_state.get("bull_history", "")
        if bull_history:
            bull_signal = TradingSignal.BUY  # Bull researcher is always bullish
            bull_confidence = self._extract_confidence_for_testing(bull_history)
            records.append(
                DecisionRecord(
                    ticker=ticker,
                    trade_date=trade_date,
                    run_id=run_id,
                    agent_name="Bull Researcher",
                    agent_type="researcher",
                    decision=bull_signal.value,
                    reasoning=bull_history[:1000] if len(bull_history) > 1000 else bull_history,
                    bull_signal=bull_signal,
                    confidence=bull_confidence,
                )
            )

        # Extract bear researcher position
        bear_history = debate_state.get("bear_history", "")
        if bear_history:
            bear_signal = TradingSignal.SELL  # Bear researcher is always bearish
            bear_confidence = self._extract_confidence_for_testing(bear_history)
            records.append(
                DecisionRecord(
                    ticker=ticker,
                    trade_date=trade_date,
                    run_id=run_id,
                    agent_name="Bear Researcher",
                    agent_type="researcher",
                    decision=bear_signal.value,
                    reasoning=bear_history[:1000] if len(bear_history) > 1000 else bear_history,
                    bear_signal=bear_signal,
                    confidence=bear_confidence,
                )
            )

        # Extract investment judge decision
        judge_decision = debate_state.get("judge_decision", "")
        investment_plan = final_state.get("investment_plan", "")
        if judge_decision or investment_plan:
            # Extract signal from judge decision or investment plan
            plan_content = judge_decision or investment_plan
            plan_signal = self._extract_signal(plan_content)
            plan_confidence = self._extract_confidence_for_testing(plan_content)

            records.append(
                DecisionRecord(
                    ticker=ticker,
                    trade_date=trade_date,
                    run_id=run_id,
                    agent_name="Investment Judge",
                    agent_type="manager",
                    decision=plan_signal.value,
                    reasoning=plan_content[:1000] if len(plan_content) > 1000 else plan_content,
                    final_signal=plan_signal,
                    confidence=plan_confidence,
                )
            )

        # Add structured debate state to metadata
        if records:
            structured_debate = DebateState(
                bull_history=debate_state.get("bull_history", ""),
                bear_history=debate_state.get("bear_history", ""),
                judge_decision=debate_state.get("judge_decision", ""),
                history=debate_state.get("history", ""),
                current_response=debate_state.get("current_response", ""),
                count=debate_state.get("count", 0),
            )
            for record in records:
                record.debate_state = structured_debate

        return records

    def _extract_trader_decision(
        self,
        final_state: Dict[str, Any],
        ticker: str,
        trade_date: str,
        run_id: Optional[str],
    ) -> Optional[DecisionRecord]:
        """Extract decision from trader investment plan.

        Args:
            final_state: Final AgentState
            ticker: Stock ticker
            trade_date: Trade date
            run_id: Run identifier

        Returns:
            DecisionRecord for trader, or None if no plan
        """
        trader_plan = final_state.get("trader_investment_plan", "")
        if not trader_plan:
            return None

        trader_signal = self._extract_signal(trader_plan)
        trader_confidence = self._extract_confidence_for_testing(trader_plan)

        return DecisionRecord(
            ticker=ticker,
            trade_date=trade_date,
            run_id=run_id,
            agent_name="Trader",
            agent_type="trader",
            decision=trader_signal.value,
            reasoning=trader_plan[:1000] if len(trader_plan) > 1000 else trader_plan,
            final_signal=trader_signal,
            confidence=trader_confidence,
        )

    def _extract_risk_decision(
        self,
        final_state: Dict[str, Any],
        ticker: str,
        trade_date: str,
        run_id: Optional[str],
    ) -> Optional[DecisionRecord]:
        """Extract decision from risk debate state.

        Args:
            final_state: Final AgentState
            ticker: Stock ticker
            trade_date: Trade date
            run_id: Run identifier

        Returns:
            DecisionRecord for risk judge, or None if no decision
        """
        risk_debate_state = final_state.get("risk_debate_state", {})
        if not risk_debate_state:
            return None

        judge_decision = risk_debate_state.get("judge_decision", "")
        if not judge_decision:
            return None

        risk_signal = self._extract_signal(judge_decision)
        risk_confidence = self._extract_confidence_for_testing(judge_decision)

        return DecisionRecord(
            ticker=ticker,
            trade_date=trade_date,
            run_id=run_id,
            agent_name="Risk Judge",
            agent_type="risk_judge",
            decision=risk_signal.value,
            reasoning=judge_decision[:1000] if len(judge_decision) > 1000 else judge_decision,
            final_signal=risk_signal,
            confidence=risk_confidence,
        )

    def _extract_final_decision(
        self,
        final_state: Dict[str, Any],
        ticker: str,
        trade_date: str,
        run_id: Optional[str],
    ) -> Optional[DecisionRecord]:
        """Extract final trade decision.

        Args:
            final_state: Final AgentState
            ticker: Stock ticker
            trade_date: Trade date
            run_id: Run identifier

        Returns:
            DecisionRecord for final decision, or None if no decision
        """
        final_decision = final_state.get("final_trade_decision", "")
        if not final_decision:
            return None

        final_signal = self._extract_signal(final_decision)
        final_confidence = self._extract_confidence_for_testing(final_decision)

        return DecisionRecord(
            ticker=ticker,
            trade_date=trade_date,
            run_id=run_id,
            agent_name="Final Decision",
            agent_type="manager",
            decision=final_signal.value,
            reasoning=final_decision[:1000] if len(final_decision) > 1000 else final_decision,
            final_signal=final_signal,
            confidence=final_confidence,
        )

    def _extract_signal(self, content: str) -> TradingSignal:
        """Extract trading signal from report content.

        Reuses the signal extraction pattern from agent_tracker.py.

        Args:
            content: Report content to parse

        Returns:
            TradingSignal enum value
        """
        if not content:
            return TradingSignal.UNKNOWN

        # Look for explicit recommendations
        content_upper = content.upper()

        # Check for explicit BUY/SELL/HOLD keywords first
        if "**RECOMMENDATION:" in content_upper:
            for signal in [TradingSignal.BUY, TradingSignal.SELL, TradingSignal.HOLD]:
                if signal.value in content_upper:
                    return signal

        # Look for "FINAL TRANSACTION PROPOSAL"
        if "FINAL TRANSACTION PROPOSAL" in content_upper:
            for signal in [TradingSignal.BUY, TradingSignal.SELL, TradingSignal.HOLD]:
                if signal.value in content_upper:
                    return signal

        # Check for bullish/bearish language
        buy_indicators = [
            "recommendation: buy",
            "recommends buy",
            "advises buy",
            "suggests buy",
        ]
        sell_indicators = [
            "recommendation: sell",
            "recommends sell",
            "advises sell",
            "suggests sell",
        ]
        hold_indicators = [
            "recommendation: hold",
            "recommends hold",
            "advises hold",
            "suggests hold",
        ]

        for indicator in buy_indicators:
            if indicator in content_upper:
                return TradingSignal.BUY

        for indicator in sell_indicators:
            if indicator in content_upper:
                return TradingSignal.SELL

        for indicator in hold_indicators:
            if indicator in content_upper:
                return TradingSignal.HOLD

        # Fallback: count bullish vs bearish words
        bullish_words = ["buy", "bullish", "positive", "growth", "opportunity", "undervalued"]
        bearish_words = ["sell", "bearish", "negative", "risk", "concern", "overvalued"]

        content_lower = content.lower()
        bullish_count = sum(1 for word in bullish_words if word in content_lower)
        bearish_count = sum(1 for word in bearish_words if word in content_lower)

        if bullish_count > bearish_count * 1.5:
            return TradingSignal.BUY
        elif bearish_count > bullish_count * 1.5:
            return TradingSignal.SELL

        return TradingSignal.UNKNOWN

    def _extract_confidence_for_testing(
        self, reasoning: str
    ) -> Optional[float]:
        """Extract confidence from reasoning text for testing.

        Helper method for extracting confidence scores from agent reasoning.
        Uses the configured confidence scorer.

        Args:
            reasoning: Agent reasoning text

        Returns:
            Confidence score between 0-1, or None if extraction fails
        """
        try:
            confidence_result = self.confidence_scorer.score(agent_output=reasoning)
            return confidence_result.score
        except Exception as e:
            logger.warning(f"Confidence extraction failed: {e}")
            return None

    def _compute_system_confidence(self, records: List[DecisionRecord]) -> None:
        """Compute system-level confidence for final decision record.

        Aggregates individual agent confidences into system-level confidence
        and populates the final decision record with the results.

        Args:
            records: List of DecisionRecord objects (modified in place)
        """
        # Find final decision record (portfolio_manager or risk_judge)
        final_record = None
        for record in records:
            if record.agent_type in ("portfolio_manager", "risk_judge", "manager"):
                final_record = record
                break

        if not final_record:
            logger.debug("No final decision record found for system confidence")
            return

        # Collect individual confidences from all records
        agent_confidences = {}
        for record in records:
            if record.confidence is not None and record.agent_name:
                agent_confidences[record.agent_name] = record.confidence

        if not agent_confidences:
            logger.debug("No individual confidences found for aggregation")
            return

        # Compute aggregated system confidence
        try:
            system_conf = self.aggregator.aggregate(agent_confidences)
            final_record.system_confidence = system_conf
            final_record.agent_confidences = agent_confidences

            logger.debug(
                f"System confidence computed: {system_conf:.3f} from {len(agent_confidences)} agents",
                extra={
                    "system_confidence": system_conf,
                    "agent_count": len(agent_confidences),
                    "aggregation_method": self.aggregator.method,
                },
            )
        except Exception as e:
            logger.warning(f"System confidence aggregation failed: {e}")
            # Don't fail the entire extraction if aggregation fails
            return
