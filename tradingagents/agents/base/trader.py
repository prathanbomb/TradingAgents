"""Base trader class and factory for creating trader agents."""

import functools
from dataclasses import dataclass
from typing import Callable


@dataclass
class TraderConfig:
    """Configuration for a trader agent.

    Attributes:
        name: The trader's name (e.g., "trader")
        display_name: Display name for output (e.g., "Trader")
        system_message: The trader's instructions
    """

    name: str
    display_name: str
    system_message: str


class BaseTrader:
    """Base class for trader agents.

    Handles trading decisions with memory integration.
    """

    def __init__(self, llm, memory, config: TraderConfig):
        """Initialize the trader.

        Args:
            llm: The language model to use
            memory: The memory instance for retrieving past experiences
            config: The trader configuration
        """
        self.llm = llm
        self.memory = memory
        self.config = config

    def create_node(self) -> Callable:
        """Create the trader node function.

        Returns:
            A function that can be used as a graph node
        """
        config = self.config
        llm = self.llm
        memory = self.memory

        def trader_node(state, name) -> dict:
            company_name = state["company_of_interest"]
            investment_plan = state["investment_plan"]
            market_report = state["market_report"]
            sentiment_report = state["sentiment_report"]
            news_report = state["news_report"]
            fundamentals_report = state["fundamentals_report"]

            # Build current situation for memory lookup
            curr_situation = f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
            past_memories = memory.get_memories(curr_situation, n_matches=2)

            past_memory_str = ""
            if past_memories:
                for rec in past_memories:
                    past_memory_str += rec["recommendation"] + "\n\n"
            else:
                past_memory_str = "No past memories found."

            # Build messages
            context = {
                "role": "user",
                "content": f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}\n\nLeverage these insights to make an informed and strategic decision.",
            }

            messages = [
                {
                    "role": "system",
                    "content": config.system_message.format(past_memory_str=past_memory_str),
                },
                context,
            ]

            result = llm.invoke(messages)

            return {
                "messages": [result],
                "trader_investment_plan": result.content,
                "sender": name,
            }

        return functools.partial(trader_node, name=config.display_name)


def create_trader_from_config(llm, memory, config: TraderConfig) -> Callable:
    """Factory function to create a trader node from configuration.

    Args:
        llm: The language model to use
        memory: The memory instance
        config: The trader configuration

    Returns:
        A node function for the trader
    """
    return BaseTrader(llm, memory, config).create_node()
