"""Agent prediction and outcome tracking.

This module tracks individual agent predictions and their actual outcomes
to measure performance over time.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class TradingSignal(Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_string(cls, value: str) -> "TradingSignal":
        """Parse signal from string."""
        value_upper = value.upper().strip()
        for signal in cls:
            if signal.value in value_upper or signal.name in value_upper:
                return signal
        # Try to detect based on keywords
        if "buy" in value_upper or "long" in value_upper or "bull" in value_upper:
            return cls.BUY
        elif "sell" in value_upper or "short" in value_upper or "bear" in value_upper:
            return cls.SELL
        return cls.UNKNOWN

    @property
    def is_bullish(self) -> bool:
        """Check if signal is bullish."""
        return self == TradingSignal.BUY

    @property
    def is_bearish(self) -> bool:
        """Check if signal is bearish."""
        return self == TradingSignal.SELL


@dataclass
class PredictionRecord:
    """Record of an agent's prediction and its outcome."""

    # Context
    ticker: str
    trade_date: str  # YYYY-MM-DD format
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Predictions by agent type
    market_signal: TradingSignal = TradingSignal.UNKNOWN
    market_report: str = ""
    sentiment_signal: TradingSignal = TradingSignal.UNKNOWN
    sentiment_report: str = ""
    news_signal: TradingSignal = TradingSignal.UNKNOWN
    news_report: str = ""
    fundamentals_signal: TradingSignal = TradingSignal.UNKNOWN
    fundamentals_report: str = ""

    # Research team predictions
    bull_signal: TradingSignal = TradingSignal.UNKNOWN
    bear_signal: TradingSignal = TradingSignal.UNKNOWN
    investment_plan_signal: TradingSignal = TradingSignal.UNKNOWN
    investment_plan_report: str = ""

    # Trader prediction
    trader_signal: TradingSignal = TradingSignal.UNKNOWN
    trader_plan_report: str = ""

    # Final decision
    final_signal: TradingSignal = TradingSignal.UNKNOWN
    final_decision_report: str = ""

    # Outcome data (filled later)
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    hold_days: int = 7
    return_pct: Optional[float] = None
    outcome_calculated: bool = False

    # Performance flags
    final_correct: Optional[bool] = None  # Was the final decision correct?

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "ticker": self.ticker,
            "trade_date": self.trade_date,
            "timestamp": self.timestamp,
            "market_signal": self.market_signal.value,
            "sentiment_signal": self.sentiment_signal.value,
            "news_signal": self.news_signal.value,
            "fundamentals_signal": self.fundamentals_signal.value,
            "bull_signal": self.bull_signal.value,
            "bear_signal": self.bear_signal.value,
            "investment_plan_signal": self.investment_plan_signal.value,
            "trader_signal": self.trader_signal.value,
            "final_signal": self.final_signal.value,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "hold_days": self.hold_days,
            "return_pct": self.return_pct,
            "outcome_calculated": self.outcome_calculated,
            "final_correct": self.final_correct,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionRecord":
        """Create from dictionary."""
        # Convert signal strings back to enums
        signal_fields = [
            "market_signal", "sentiment_signal", "news_signal", "fundamentals_signal",
            "bull_signal", "bear_signal", "investment_plan_signal", "trader_signal", "final_signal"
        ]
        for field in signal_fields:
            if field in data and isinstance(data[field], str):
                data[field] = TradingSignal.from_string(data[field])

        return cls(**data)

    def extract_signals_from_reports(self) -> None:
        """Extract trading signals from report content."""
        # Extract signals from analyst reports
        if self.market_report:
            self.market_signal = self._extract_signal(self.market_report)
        if self.sentiment_report:
            self.sentiment_signal = self._extract_signal(self.sentiment_report)
        if self.news_report:
            self.news_signal = self._extract_signal(self.news_report)
        if self.fundamentals_report:
            self.fundamentals_signal = self._extract_signal(self.fundamentals_report)

        # Extract from investment plan
        if self.investment_plan_report:
            self.investment_plan_signal = self._extract_signal(self.investment_plan_report)
            # Bull researcher is typically bullish, Bear is bearish
            self.bull_signal = TradingSignal.BUY if self.investment_plan_signal.is_bullish else TradingSignal.UNKNOWN
            self.bear_signal = TradingSignal.SELL if self.investment_plan_signal.is_bearish else TradingSignal.UNKNOWN

        # Extract from trader plan
        if self.trader_plan_report:
            self.trader_signal = self._extract_signal(self.trader_plan_report)

        # Extract from final decision
        if self.final_decision_report:
            self.final_signal = self._extract_signal(self.final_decision_report)

    def _extract_signal(self, content: str) -> TradingSignal:
        """Extract trading signal from report content."""
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
        buy_indicators = ["recommendation: buy", "recommends buy", "advises buy", "suggests buy"]
        sell_indicators = ["recommendation: sell", "recommends sell", "advises sell", "suggests sell"]
        hold_indicators = ["recommendation: hold", "recommends hold", "advises hold", "suggests hold"]

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


class AgentTracker:
    """Track agent predictions and outcomes over time."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize agent tracker.

        Args:
            storage_path: Path to store prediction records. Defaults to ./data/predictions/
        """
        if storage_path is None:
            storage_path = Path("./data/predictions")
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def record_prediction(
        self,
        ticker: str,
        trade_date: str,
        final_state: Dict[str, Any],
        decision: str,
    ) -> PredictionRecord:
        """Record a prediction from the trading graph.

        Args:
            ticker: Stock ticker symbol
            trade_date: Trade date (YYYY-MM-DD)
            final_state: Final state from graph.propagate()
            decision: Final decision string

        Returns:
            PredictionRecord with all extracted predictions
        """
        record = PredictionRecord(
            ticker=ticker,
            trade_date=trade_date,
            market_report=final_state.get("market_report", ""),
            sentiment_report=final_state.get("sentiment_report", ""),
            news_report=final_state.get("news_report", ""),
            fundamentals_report=final_state.get("fundamentals_report", ""),
            investment_plan_report=final_state.get("investment_plan", ""),
            trader_plan_report=final_state.get("trader_investment_plan", ""),
            final_decision_report=final_state.get("final_trade_decision", ""),
        )

        # Extract signals from reports
        record.extract_signals_from_reports()

        # Override final signal if decision was provided
        if decision:
            record.final_signal = TradingSignal.from_string(decision)

        # Save to storage
        self._save_record(record)

        logger.info(f"Recorded prediction for {ticker} on {trade_date}: {record.final_signal.value}")
        return record

    def _save_record(self, record: PredictionRecord) -> None:
        """Save prediction record to storage.

        Args:
            record: Prediction record to save
        """
        ticker_dir = self.storage_path / record.ticker
        ticker_dir.mkdir(exist_ok=True)

        filename = f"{record.trade_date}.json"
        filepath = ticker_dir / filename

        with open(filepath, "w") as f:
            json.dump(record.to_dict(), f, indent=2)

        logger.debug(f"Saved prediction record to {filepath}")

    def load_predictions(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[PredictionRecord]:
        """Load prediction records from storage.

        Args:
            ticker: Filter by ticker (if None, load all)
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)

        Returns:
            List of prediction records
        """
        records = []

        # Determine which directories to search
        if ticker:
            search_dirs = [self.storage_path / ticker]
        else:
            search_dirs = [d for d in self.storage_path.iterdir() if d.is_dir()]

        for ticker_dir in search_dirs:
            if not ticker_dir.exists():
                continue

            for filepath in ticker_dir.glob("*.json"):
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                    record = PredictionRecord.from_dict(data)

                    # Filter by date range
                    if start_date and record.trade_date < start_date:
                        continue
                    if end_date and record.trade_date > end_date:
                        continue

                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to load {filepath}: {e}")

        # Sort by date (most recent first)
        records.sort(key=lambda r: r.trade_date, reverse=True)
        return records

    def get_prediction(self, ticker: str, trade_date: str) -> Optional[PredictionRecord]:
        """Get a specific prediction record.

        Args:
            ticker: Stock ticker symbol
            trade_date: Trade date (YYYY-MM-DD)

        Returns:
            Prediction record if found, None otherwise
        """
        filepath = self.storage_path / ticker / f"{trade_date}.json"
        if not filepath.exists():
            return None

        try:
            with open(filepath) as f:
                data = json.load(f)
            return PredictionRecord.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load prediction for {ticker} on {trade_date}: {e}")
            return None

    def update_outcome(
        self,
        ticker: str,
        trade_date: str,
        entry_price: float,
        exit_price: float,
        hold_days: int = 7,
    ) -> Optional[PredictionRecord]:
        """Update prediction record with outcome data.

        Args:
            ticker: Stock ticker symbol
            trade_date: Trade date (YYYY-MM-DD)
            entry_price: Price at trade date
            exit_price: Price after hold_days
            hold_days: Number of days held

        Returns:
            Updated prediction record, or None if not found
        """
        record = self.get_prediction(ticker, trade_date)
        if not record:
            logger.warning(f"No prediction found for {ticker} on {trade_date}")
            return None

        # Update outcome data
        record.entry_price = entry_price
        record.exit_price = exit_price
        record.hold_days = hold_days
        record.return_pct = ((exit_price - entry_price) / entry_price) * 100
        record.outcome_calculated = True

        # Determine if final decision was correct
        if record.final_signal == TradingSignal.BUY:
            record.final_correct = record.return_pct > 0
        elif record.final_signal == TradingSignal.SELL:
            record.final_correct = record.return_pct < 0
        elif record.final_signal == TradingSignal.HOLD:
            # Hold is correct if return is within a small range
            record.final_correct = abs(record.return_pct) < 2.0

        # Save updated record
        self._save_record(record)

        logger.info(
            f"Updated outcome for {ticker} on {trade_date}: "
            f"{record.return_pct:.2f}% return, "
            f"final_correct={record.final_correct}"
        )
        return record
