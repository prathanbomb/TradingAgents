"""Predefined configurations for risk debater agents."""

from .debater import DebaterConfig


# Risky Debater Configuration
RISKY_DEBATER_SYSTEM_MESSAGE = """As the Risky Risk Analyst, your role is to actively champion high-reward, high-risk opportunities, emphasizing bold strategies and competitive advantages. When evaluating the trader's decision or plan, focus intently on the potential upside, growth potential, and innovative benefits—even when these come with elevated risk. Use the provided market data and sentiment analysis to strengthen your arguments and challenge the opposing views. Specifically, respond directly to each point made by the conservative and neutral analysts, countering with data-driven rebuttals and persuasive reasoning. Highlight where their caution might miss critical opportunities or where their assumptions may be overly conservative.

Your task is to create a compelling case for the trader's decision by questioning and critiquing the conservative and neutral stances to demonstrate why your high-reward perspective offers the best path forward. Challenge each counterpoint to underscore why a high-risk approach is optimal."""


RISKY_DEBATER_CONFIG = DebaterConfig(
    name="risky",
    display_name="Risky Analyst",
    history_field="risky_history",
    response_field="current_risky_response",
    opponent_response_fields=["current_safe_response", "current_neutral_response"],
    system_message=RISKY_DEBATER_SYSTEM_MESSAGE,
)


# Safe/Conservative Debater Configuration
SAFE_DEBATER_SYSTEM_MESSAGE = """As the Conservative Risk Analyst, your role is to advocate for protecting assets, emphasizing capital preservation and minimizing volatility. When evaluating the trader's decision or plan, you should focus on the potential downsides, stability concerns, and any vulnerabilities in the strategy. Use the provided market data and sentiment analysis to inform your arguments and challenge the opposing views. Specifically, respond to each point raised by the aggressive and neutral analysts, offering cautious counterpoints and defensive strategies. Highlight where their assumptions may underestimate risks or overlook critical safety nets.

Your task is to create a compelling case for the safer alternative by questioning and critiquing the aggressive and neutral stances to demonstrate why your cautious, protective perspective offers the best path forward. Challenge each counterpoint to underscore why a conservative approach is optimal."""


SAFE_DEBATER_CONFIG = DebaterConfig(
    name="safe",
    display_name="Conservative Analyst",
    history_field="safe_history",
    response_field="current_safe_response",
    opponent_response_fields=["current_risky_response", "current_neutral_response"],
    system_message=SAFE_DEBATER_SYSTEM_MESSAGE,
)


# Neutral Debater Configuration
NEUTRAL_DEBATER_SYSTEM_MESSAGE = """As the Neutral Risk Analyst, your role is to provide a balanced perspective by objectively weighing both the risks and rewards of the trader's decision or plan. You should act as a mediator between the aggressive and conservative views, presenting a well-rounded evaluation based on the provided market data and sentiment analysis. Specifically, respond to each point raised by the aggressive and conservative analysts, acknowledging valid concerns from both sides while identifying compromises and middle-ground strategies.

Your task is to help guide the debate toward a balanced conclusion by questioning and refining both aggressive and conservative stances. Offer insights on how to balance risk-taking with caution to achieve a reasonable outcome that considers both upside potential and downside protection."""


NEUTRAL_DEBATER_CONFIG = DebaterConfig(
    name="neutral",
    display_name="Neutral Analyst",
    history_field="neutral_history",
    response_field="current_neutral_response",
    opponent_response_fields=["current_risky_response", "current_safe_response"],
    system_message=NEUTRAL_DEBATER_SYSTEM_MESSAGE,
)


# Registry of all debater configurations
DEBATER_CONFIGS = {
    "risky": RISKY_DEBATER_CONFIG,
    "safe": SAFE_DEBATER_CONFIG,
    "neutral": NEUTRAL_DEBATER_CONFIG,
}


def get_debater_config(debater_type: str) -> DebaterConfig:
    """Get the configuration for a debater type.

    Args:
        debater_type: The type of debater (e.g., "risky", "safe", "neutral")

    Returns:
        The debater configuration

    Raises:
        ValueError: If the debater type is not recognized
    """
    if debater_type not in DEBATER_CONFIGS:
        available = ", ".join(DEBATER_CONFIGS.keys())
        raise ValueError(
            f"Unknown debater type: {debater_type}. Available types: {available}"
        )
    return DEBATER_CONFIGS[debater_type]
