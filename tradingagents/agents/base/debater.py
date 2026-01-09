"""Base debater class and factory for creating risk debate agents."""

from dataclasses import dataclass, field
from typing import Callable, List


@dataclass
class DebaterConfig:
    """Configuration for a risk debater agent.

    Attributes:
        name: The debater's name (e.g., "risky", "safe", "neutral")
        display_name: Display name for output (e.g., "Risky Analyst")
        history_field: The state field for this debater's history
        response_field: The state field for this debater's current response
        opponent_response_fields: List of opponent response field names
        system_message: The debater's perspective and instructions
    """

    name: str
    display_name: str
    history_field: str
    response_field: str
    opponent_response_fields: List[str]
    system_message: str


class BaseDebater:
    """Base class for risk debater agents.

    Handles three-way debate state management without memory integration.
    """

    def __init__(self, llm, config: DebaterConfig):
        """Initialize the debater.

        Args:
            llm: The language model to use
            config: The debater configuration
        """
        self.llm = llm
        self.config = config

    def create_node(self) -> Callable:
        """Create the debater node function.

        Returns:
            A function that can be used as a graph node
        """
        config = self.config
        llm = self.llm

        def debater_node(state) -> dict:
            # Extract debate state
            risk_debate_state = state["risk_debate_state"]
            history = risk_debate_state.get("history", "")
            own_history = risk_debate_state.get(config.history_field, "")

            # Get opponent responses
            opponent_responses = {}
            for field_name in config.opponent_response_fields:
                opponent_responses[field_name] = risk_debate_state.get(field_name, "")

            # Extract research reports
            market_report = state["market_report"]
            sentiment_report = state["sentiment_report"]
            news_report = state["news_report"]
            fundamentals_report = state["fundamentals_report"]

            # Get trader's decision
            trader_decision = state["trader_investment_plan"]

            # Build opponent arguments string
            opponent_args = ""
            for field_name, response in opponent_responses.items():
                if response:
                    # Convert field name to readable format
                    readable_name = field_name.replace("current_", "").replace("_response", "")
                    opponent_args += f"Last arguments from {readable_name} analyst: {response}\n"

            # Build prompt
            prompt = f"""{config.system_message}

Trader's Decision:
{trader_decision}

Market Research Report: {market_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}

Current conversation history: {history}
{opponent_args}
If there are no responses from the other viewpoints, do not hallucinate and just present your point.

Engage actively by addressing any specific concerns raised, refuting the weaknesses in their logic. Maintain a focus on debating and persuading, not just presenting data. Output conversationally as if you are speaking without any special formatting."""

            # Generate response
            response = llm.invoke(prompt)
            argument = f"{config.display_name}: {response.content}"

            # Build new state preserving all fields
            new_risk_debate_state = {
                "history": history + "\n" + argument,
                config.history_field: own_history + "\n" + argument,
                "latest_speaker": config.name.capitalize(),
                config.response_field: argument,
                "count": risk_debate_state["count"] + 1,
            }

            # Preserve other history and response fields
            all_history_fields = ["risky_history", "safe_history", "neutral_history"]
            all_response_fields = [
                "current_risky_response",
                "current_safe_response",
                "current_neutral_response",
            ]

            for hf in all_history_fields:
                if hf != config.history_field:
                    new_risk_debate_state[hf] = risk_debate_state.get(hf, "")

            for rf in all_response_fields:
                if rf != config.response_field:
                    new_risk_debate_state[rf] = risk_debate_state.get(rf, "")

            return {"risk_debate_state": new_risk_debate_state}

        return debater_node


def create_debater_from_config(llm, config: DebaterConfig) -> Callable:
    """Factory function to create a debater node from configuration.

    Args:
        llm: The language model to use
        config: The debater configuration

    Returns:
        A node function for the debater
    """
    return BaseDebater(llm, config).create_node()
