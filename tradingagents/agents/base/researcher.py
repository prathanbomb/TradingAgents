"""Base researcher class and factory for creating debate agents."""

from dataclasses import dataclass
from typing import Callable, Optional

from tradingagents.agents.utils.memory import FinancialSituationMemory, get_situation_memories


@dataclass
class ResearcherConfig:
    """Configuration for a researcher agent in investment debates.

    Attributes:
        name: The researcher's name (e.g., "bull", "bear")
        display_name: Display name for output (e.g., "Bull Analyst")
        history_field: The state field for this researcher's history
        opponent_history_field: The state field for opponent's history
        system_message: The researcher's perspective and instructions
    """

    name: str
    display_name: str
    history_field: str
    opponent_history_field: str
    system_message: str


class BaseResearcher:
    """Base class for researcher agents in investment debates.

    Handles memory integration, debate state management, and argument generation.
    """

    def __init__(
        self,
        llm,
        memory: FinancialSituationMemory,
        config: ResearcherConfig,
    ):
        """Initialize the researcher.

        Args:
            llm: The language model to use
            memory: Memory instance for retrieving past situations
            config: The researcher configuration
        """
        self.llm = llm
        self.memory = memory
        self.config = config

    def create_node(self) -> Callable:
        """Create the researcher node function.

        Returns:
            A function that can be used as a graph node
        """
        config = self.config
        llm = self.llm
        memory = self.memory

        def researcher_node(state) -> dict:
            # Extract debate state
            investment_debate_state = state["investment_debate_state"]
            history = investment_debate_state.get("history", "")
            own_history = investment_debate_state.get(config.history_field, "")
            current_response = investment_debate_state.get("current_response", "")

            # Extract research reports
            market_report = state["market_report"]
            sentiment_report = state["sentiment_report"]
            news_report = state["news_report"]
            fundamentals_report = state["fundamentals_report"]

            # Retrieve relevant past memories
            past_memory_str = get_situation_memories(
                memory, market_report, sentiment_report, news_report, fundamentals_report
            )

            # Build prompt
            prompt = f"""{config.system_message}

Resources available:
Market research report: {market_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Conversation history of the debate: {history}
Last opponent argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}
"""

            # Generate response
            response = llm.invoke(prompt)
            argument = f"{config.display_name}: {response.content}"

            # Update debate state
            new_investment_debate_state = {
                "history": history + "\n" + argument,
                config.history_field: own_history + "\n" + argument,
                config.opponent_history_field: investment_debate_state.get(
                    config.opponent_history_field, ""
                ),
                "current_response": argument,
                "count": investment_debate_state["count"] + 1,
            }

            return {"investment_debate_state": new_investment_debate_state}

        return researcher_node


def create_researcher_from_config(
    llm,
    memory: FinancialSituationMemory,
    config: ResearcherConfig,
) -> Callable:
    """Factory function to create a researcher node from configuration.

    Args:
        llm: The language model to use
        memory: Memory instance for retrieving past situations
        config: The researcher configuration

    Returns:
        A node function for the researcher
    """
    return BaseResearcher(llm, memory, config).create_node()
