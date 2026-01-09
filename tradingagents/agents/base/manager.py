"""Base manager class and factory for creating judge agents."""

from dataclasses import dataclass
from typing import Callable, Dict, List, Any

from tradingagents.agents.utils.memory import get_situation_memories


@dataclass
class ManagerConfig:
    """Configuration for a manager/judge agent.

    Attributes:
        name: The manager's name (e.g., "research", "risk")
        display_name: Display name for output (e.g., "Research Manager")
        debate_state_field: The state field containing debate state
        history_fields: List of history field names to preserve
        response_fields: List of response field names to preserve (for risk manager)
        output_field: The state field for the output (e.g., "investment_plan")
        output_state_field: Additional state field to update (e.g., "final_trade_decision")
        system_message: The manager's instructions
    """

    name: str
    display_name: str
    debate_state_field: str
    history_fields: List[str]
    response_fields: List[str]
    output_field: str
    output_state_field: str
    system_message: str


class BaseManager:
    """Base class for manager/judge agents.

    Handles debate judging with memory integration.
    """

    def __init__(self, llm, memory, config: ManagerConfig):
        """Initialize the manager.

        Args:
            llm: The language model to use
            memory: The memory instance for retrieving past experiences
            config: The manager configuration
        """
        self.llm = llm
        self.memory = memory
        self.config = config

    def create_node(self) -> Callable:
        """Create the manager node function.

        Returns:
            A function that can be used as a graph node
        """
        config = self.config
        llm = self.llm
        memory = self.memory

        def manager_node(state) -> dict:
            # Extract debate state
            debate_state = state[config.debate_state_field]
            history = debate_state.get("history", "")

            # Extract research reports
            market_report = state["market_report"]
            sentiment_report = state["sentiment_report"]
            news_report = state["news_report"]
            fundamentals_report = state["fundamentals_report"]

            # Retrieve relevant past memories
            past_memory_str = get_situation_memories(
                memory, market_report, sentiment_report, news_report, fundamentals_report
            )

            # Get additional context for risk manager
            trader_plan = state.get("investment_plan", "")

            # Build prompt with context
            prompt = config.system_message.format(
                history=history,
                past_memory_str=past_memory_str,
                trader_plan=trader_plan,
            )

            # Generate response
            response = llm.invoke(prompt)

            # Build new debate state preserving all fields
            new_debate_state = {
                "judge_decision": response.content,
                "history": debate_state.get("history", ""),
                "count": debate_state.get("count", 0),
            }

            # Preserve history fields
            for field in config.history_fields:
                new_debate_state[field] = debate_state.get(field, "")

            # Preserve response fields (for risk manager)
            for field in config.response_fields:
                new_debate_state[field] = debate_state.get(field, "")

            # Add current response for investment debate
            if "current_response" not in config.response_fields:
                new_debate_state["current_response"] = response.content

            # Add latest_speaker for risk debate
            if config.name == "risk":
                new_debate_state["latest_speaker"] = "Judge"

            # Build return state
            result = {config.debate_state_field: new_debate_state}

            # Add output field
            if config.output_field:
                result[config.output_field] = response.content

            # Add additional output state field if specified
            if config.output_state_field:
                result[config.output_state_field] = response.content

            return result

        return manager_node


def create_manager_from_config(llm, memory, config: ManagerConfig) -> Callable:
    """Factory function to create a manager node from configuration.

    Args:
        llm: The language model to use
        memory: The memory instance
        config: The manager configuration

    Returns:
        A node function for the manager
    """
    return BaseManager(llm, memory, config).create_node()
