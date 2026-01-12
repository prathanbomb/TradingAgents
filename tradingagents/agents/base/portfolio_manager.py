"""Portfolio Manager agent for personalized trading recommendations.

This module provides an agent that generates context-aware trading advice
based on both the TradingAgents analysis reports AND the user's actual
portfolio state (positions, transaction history, cash balance).
"""

from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional

from tradingagents.agents.utils.memory import get_situation_memories


@dataclass
class PortfolioManagerConfig:
    """Configuration for the Portfolio Manager agent.

    Attributes:
        name: The manager's name
        display_name: Display name for output
        system_message: The manager's instructions for personalized recommendations
    """

    name: str
    display_name: str
    system_message: str


class BasePortfolioManager:
    """Portfolio Manager agent for personalized trading recommendations.

    This agent takes the final trading decision and the user's current
    portfolio state to generate personalized, context-aware advice.
    """

    def __init__(self, llm, memory, config: PortfolioManagerConfig, portfolio_service=None):
        """Initialize the Portfolio Manager.

        Args:
            llm: The language model to use
            memory: The memory instance for retrieving past experiences
            config: The portfolio manager configuration
            portfolio_service: Optional service for loading portfolio data
        """
        self.llm = llm
        self.memory = memory
        self.config = config
        self.portfolio_service = portfolio_service

    def create_node(self) -> Callable:
        """Create the portfolio manager node function.

        Returns:
            A function that can be used as a graph node
        """
        config = self.config
        llm = self.llm
        memory = self.memory
        portfolio_service = self.portfolio_service

        def portfolio_manager_node(state) -> dict:
            # Extract all analysis reports
            market_report = state.get("market_report", "")
            sentiment_report = state.get("sentiment_report", "")
            news_report = state.get("news_report", "")
            fundamentals_report = state.get("fundamentals_report", "")

            # Get the trading decision and plans
            investment_plan = state.get("investment_plan", "")
            trader_plan = state.get("trader_investment_plan", "")
            final_decision = state.get("final_trade_decision", "")

            # Get company info
            company = state.get("company_of_interest", "")

            # Retrieve relevant past memories
            past_memory_str = get_situation_memories(
                memory, market_report, sentiment_report, news_report, fundamentals_report
            )

            # Load portfolio state if service is available
            portfolio_summary_str = ""
            if portfolio_service:
                try:
                    portfolio = portfolio_service.get_portfolio()
                    portfolio_summary_str = portfolio.format_summary()
                except Exception as e:
                    portfolio_summary_str = f"Unable to load portfolio: {e}"

            # Build the prompt
            prompt = config.system_message.format(
                company=company,
                portfolio_summary=portfolio_summary_str,
                market_report=market_report,
                sentiment_report=sentiment_report,
                news_report=news_report,
                fundamentals_report=fundamentals_report,
                investment_plan=investment_plan,
                trader_plan=trader_plan,
                final_decision=final_decision,
                past_memory_str=past_memory_str,
            )

            # Generate personalized recommendation
            response = llm.invoke(prompt)

            return {
                "personalized_recommendation": response.content,
            }

        return portfolio_manager_node


def create_portfolio_manager_from_config(
    llm, memory, config: PortfolioManagerConfig, portfolio_service=None
) -> Callable:
    """Factory function to create a portfolio manager node from configuration.

    Args:
        llm: The language model to use
        memory: The memory instance
        config: The portfolio manager configuration
        portfolio_service: Optional service for loading portfolio data

    Returns:
        A node function for the portfolio manager
    """
    return BasePortfolioManager(llm, memory, config, portfolio_service).create_node()
