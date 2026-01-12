"""Performance metrics calculation for agent performance tracking.

This module calculates various performance metrics for individual agents
and the overall trading system.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import statistics

from .agent_tracker import PredictionRecord, TradingSignal

logger = logging.getLogger(__name__)


@dataclass
class AgentPerformance:
    """Performance metrics for a single agent."""

    agent_name: str
    total_predictions: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0
    win_rate: float = 0.0
    avg_return: float = 0.0
    avg_return_when_correct: float = 0.0
    avg_return_when_wrong: float = 0.0
    best_trade: float = float('-inf')
    worst_trade: float = float('inf')
    sharpe_ratio: Optional[float] = None
    max_drawdown: float = 0.0
    recent_accuracy: float = 0.0  # Last 10 predictions

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "accuracy": self.accuracy,
            "win_rate": self.win_rate,
            "avg_return": self.avg_return,
            "avg_return_when_correct": self.avg_return_when_correct,
            "avg_return_when_wrong": self.avg_return_when_wrong,
            "best_trade": self.best_trade if self.best_trade != float('-inf') else None,
            "worst_trade": self.worst_trade if self.worst_trade != float('inf') else None,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "recent_accuracy": self.recent_accuracy,
        }


class PerformanceMetrics:
    """Calculate performance metrics from prediction records."""

    def __init__(self, risk_free_rate: float = 0.02):
        """Initialize performance metrics calculator.

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe ratio calculation
        """
        self.risk_free_rate = risk_free_rate

    def calculate_agent_performance(
        self,
        records: List[PredictionRecord],
        signal_field: str = "final_signal",
    ) -> AgentPerformance:
        """Calculate performance metrics for an agent.

        Args:
            records: List of prediction records with outcomes
            signal_field: Which signal field to analyze (e.g., "final_signal", "market_signal")

        Returns:
            AgentPerformance with calculated metrics
        """
        if not records:
            return AgentPerformance(agent_name=signal_field)

        # Filter records that have outcomes calculated
        records_with_outcomes = [r for r in records if r.outcome_calculated]
        if not records_with_outcomes:
            logger.warning(f"No records with outcomes for {signal_field}")
            return AgentPerformance(agent_name=signal_field)

        # Get predictions and outcomes
        predictions = []
        outcomes = []  # True if correct, False if wrong
        returns = []

        for record in records_with_outcomes:
            signal = getattr(record, signal_field, TradingSignal.UNKNOWN)
            if signal == TradingSignal.UNKNOWN:
                continue

            predictions.append(signal)
            returns.append(record.return_pct or 0.0)

            # Determine if prediction was correct
            correct = False
            if signal == TradingSignal.BUY:
                correct = record.return_pct and record.return_pct > 0
            elif signal == TradingSignal.SELL:
                correct = record.return_pct and record.return_pct < 0
            elif signal == TradingSignal.HOLD:
                correct = abs(record.return_pct or 0) < 2.0  # Within 2%

            outcomes.append(correct)

        if not predictions:
            return AgentPerformance(agent_name=signal_field)

        total_predictions = len(predictions)
        correct_predictions = sum(outcomes)
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0

        # Win rate (percentage of profitable trades)
        profitable_returns = [r for r in returns if r > 0]
        win_rate = len(profitable_returns) / len(returns) if returns else 0.0

        # Average returns
        avg_return = statistics.mean(returns) if returns else 0.0
        correct_returns = [r for r, o in zip(returns, outcomes) if o]
        wrong_returns = [r for r, o in zip(returns, outcomes) if not o]

        avg_return_when_correct = statistics.mean(correct_returns) if correct_returns else 0.0
        avg_return_when_wrong = statistics.mean(wrong_returns) if wrong_returns else 0.0

        # Best and worst trades
        best_trade = max(returns) if returns else 0.0
        worst_trade = min(returns) if returns else 0.0

        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe(returns) if len(returns) > 1 else None

        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown(returns) if returns else 0.0

        # Recent accuracy (last 10 predictions)
        recent_outcomes = outcomes[-10:] if len(outcomes) >= 10 else outcomes
        recent_accuracy = sum(recent_outcomes) / len(recent_outcomes) if recent_outcomes else 0.0

        return AgentPerformance(
            agent_name=signal_field,
            total_predictions=total_predictions,
            correct_predictions=correct_predictions,
            accuracy=accuracy,
            win_rate=win_rate,
            avg_return=avg_return,
            avg_return_when_correct=avg_return_when_correct,
            avg_return_when_wrong=avg_return_when_wrong,
            best_trade=best_trade,
            worst_trade=worst_trade,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            recent_accuracy=recent_accuracy,
        )

    def _calculate_sharpe(self, returns: List[float]) -> Optional[float]:
        """Calculate Sharpe ratio for a series of returns.

        Args:
            returns: List of percentage returns

        Returns:
            Sharpe ratio or None if calculation fails
        """
        if len(returns) < 2:
            return None

        try:
            # Convert to annualized values (assuming 7-day holding period)
            avg_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)

            if std_return == 0:
                return None

            # Annualize: assume 52 trading periods (52 weeks / 7 days per period)
            periods_per_year = 52
            annualized_return = avg_return * periods_per_year / 100
            annualized_std = std_return * (periods_per_year ** 0.5) / 100

            # Sharpe = (return - risk_free) / std
            sharpe = (annualized_return - self.risk_free_rate) / annualized_std
            return sharpe
        except (statistics.StatisticsError, ZeroDivisionError):
            return None

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from a series of returns.

        Args:
            returns: List of percentage returns

        Returns:
            Maximum drawdown as a positive percentage
        """
        if not returns:
            return 0.0

        # Calculate cumulative returns
        cumulative = [100.0]  # Start with 100
        for ret in returns:
            cumulative.append(cumulative[-1] * (1 + ret / 100))

        # Find max drawdown
        peak = cumulative[0]
        max_dd = 0.0

        for value in cumulative:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            max_dd = max(max_dd, drawdown)

        return max_dd

    def calculate_all_agent_performance(
        self,
        records: List[PredictionRecord],
    ) -> Dict[str, AgentPerformance]:
        """Calculate performance for all agent types.

        Args:
            records: List of prediction records with outcomes

        Returns:
            Dictionary mapping agent names to performance metrics
        """
        agent_types = [
            "final_signal",
            "trader_signal",
            "investment_plan_signal",
            "market_signal",
            "sentiment_signal",
            "news_signal",
            "fundamentals_signal",
            "bull_signal",
            "bear_signal",
        ]

        performances = {}
        for agent_type in agent_types:
            perf = self.calculate_agent_performance(records, agent_type)
            if perf.total_predictions > 0:
                # Use a cleaner name for display
                display_name = agent_type.replace("_signal", "").replace("_", " ").title()
                perf.agent_name = display_name
                performances[display_name] = perf

        return performances

    def calculate_bull_vs_bear_performance(
        self,
        records: List[PredictionRecord],
    ) -> Dict[str, Dict]:
        """Calculate comparative performance between Bull and Bear researchers.

        Args:
            records: List of prediction records with outcomes

        Returns:
            Dictionary with bull and bear performance comparison
        """
        bull_perf = self.calculate_agent_performance(records, "bull_signal")
        bear_perf = self.calculate_agent_performance(records, "bear_signal")

        return {
            "Bull": {
                "accuracy": bull_perf.accuracy,
                "win_rate": bull_perf.win_rate,
                "avg_return": bull_perf.avg_return,
                "total_predictions": bull_perf.total_predictions,
                "recent_accuracy": bull_perf.recent_accuracy,
            },
            "Bear": {
                "accuracy": bear_perf.accuracy,
                "win_rate": bear_perf.win_rate,
                "avg_return": bear_perf.avg_return,
                "total_predictions": bear_perf.total_predictions,
                "recent_accuracy": bear_perf.recent_accuracy,
            },
            "winner": "Bull" if bull_perf.avg_return > bear_perf.avg_return else "Bear",
        }


@dataclass
class PerformanceReport:
    """Generated performance report."""

    ticker: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_predictions: int = 0
    agent_performances: Dict[str, AgentPerformance] = field(default_factory=dict)
    bull_vs_bear: Dict = field(default_factory=dict)
    overall_accuracy: float = 0.0
    overall_avg_return: float = 0.0

    def generate_markdown(self) -> str:
        """Generate markdown performance report.

        Returns:
            Markdown formatted report
        """
        lines = []

        # Header
        lines.append("# Agent Performance Report")
        lines.append("")

        if self.ticker:
            lines.append(f"**Ticker:** {self.ticker}")
        if self.start_date and self.end_date:
            lines.append(f"**Period:** {self.start_date} to {self.end_date}")
        lines.append(f"**Total Predictions:** {self.total_predictions}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Overall summary
        lines.append("## Overall Performance")
        lines.append("")
        lines.append(f"- **Accuracy:** {self.overall_accuracy:.1%}")
        lines.append(f"- **Average Return:** {self.overall_avg_return:.2f}%")
        lines.append("")

        # Agent comparison table
        lines.append("## Agent Performance Comparison")
        lines.append("")
        lines.append("| Agent | Total | Accuracy | Win Rate | Avg Return | Sharpe | Recent (10)")
        lines.append("|-------|-------|----------|----------|------------|--------|-------------|")

        # Sort by avg return
        sorted_agents = sorted(
            self.agent_performances.items(),
            key=lambda x: x[1].avg_return,
            reverse=True
        )

        for agent_name, perf in sorted_agents:
            sharpe_str = f"{perf.sharpe_ratio:.2f}" if perf.sharpe_ratio else "N/A"
            lines.append(
                f"| {agent_name} | {perf.total_predictions} | {perf.accuracy:.1%} | "
                f"{perf.win_rate:.1%} | {perf.avg_return:+.2f}% | {sharpe_str} | "
                f"{perf.recent_accuracy:.1%} |"
            )
        lines.append("")

        # Bull vs Bear comparison
        if self.bull_vs_bear:
            lines.append("## Bull vs Bear Researcher Showdown")
            lines.append("")
            bull = self.bull_vs_bear.get("Bull", {})
            bear = self.bull_vs_bear.get("Bear", {})
            winner = self.bull_vs_bear.get("winner", "Tie")

            lines.append(f"**Winner:** {winner}")
            lines.append("")
            lines.append("| Metric | Bull | Bear | Winner |")
            lines.append("|--------|------|------|-------|")

            metrics_to_compare = ["accuracy", "win_rate", "avg_return"]
            for metric in metrics_to_compare:
                bull_val = bull.get(metric, 0)
                bear_val = bear.get(metric, 0)
                if metric == "accuracy" or metric == "win_rate":
                    bull_str = f"{bull_val:.1%}"
                    bear_str = f"{bear_val:.1%}"
                    winner = "Bull" if bull_val > bear_val else "Bear" if bear_val > bull_val else "Tie"
                else:
                    bull_str = f"{bull_val:+.2f}%"
                    bear_str = f"{bear_val:+.2f}%"
                    winner = "Bull" if bull_val > bear_val else "Bear" if bear_val > bull_val else "Tie"

                lines.append(f"| {metric.title().replace('_', ' ')} | {bull_str} | {bear_str} | {winner} |")
            lines.append("")

        # Top performers section
        lines.append("## Top Performers")
        lines.append("")
        lines.append("### Most Accurate")
        if self.agent_performances:
            most_accurate = max(self.agent_performances.values(), key=lambda p: p.accuracy, default=None)
            if most_accurate and most_accurate.total_predictions > 0:
                lines.append(f"- **{most_accurate.agent_name}**: {most_accurate.accuracy:.1%} accuracy")
                lines.append("")

        lines.append("### Highest Average Return")
        if self.agent_performances:
            highest_return = max(self.agent_performances.values(), key=lambda p: p.avg_return, default=None)
            if highest_return and highest_return.total_predictions > 0:
                lines.append(f"- **{highest_return.agent_name}**: {highest_return.avg_return:+.2f}% avg return")
                lines.append("")

        lines.append("### Best Sharpe Ratio")
        sharpe_agents = [p for p in self.agent_performances.values() if p.sharpe_ratio is not None]
        if sharpe_agents:
            best_sharpe = max(sharpe_agents, key=lambda p: p.sharpe_ratio)
            lines.append(f"- **{best_sharpe.agent_name}**: Sharpe ratio of {best_sharpe.sharpe_ratio:.2f}")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by TradingAgents Agent Performance Tracker*")

        return "\n".join(lines)

    def generate_summary(self) -> str:
        """Generate a short text summary of performance.

        Returns:
            Text summary
        """
        if not self.agent_performances:
            return "No performance data available."

        # Find best and worst performers
        sorted_agents = sorted(
            self.agent_performances.items(),
            key=lambda x: x[1].avg_return,
            reverse=True
        )

        best_agent, best_perf = sorted_agents[0]
        worst_agent, worst_perf = sorted_agents[-1]

        summary = [
            f"Performance Report ({self.total_predictions} predictions)",
            "",
            f"Best: {best_agent} with {best_perf.avg_return:+.2f}% avg return",
            f"Worst: {worst_agent} with {worst_perf.avg_return:+.2f}% avg return",
            f"Overall accuracy: {self.overall_accuracy:.1%}",
        ]

        if self.bull_vs_bear:
            winner = self.bull_vs_bear.get("winner", "Tie")
            summary.append(f"Bull vs Bear winner: {winner}")

        return "\n".join(summary)
