"""Predefined configurations for trader agents."""

from .trader import TraderConfig


# Trader Configuration
TRADER_SYSTEM_MESSAGE = """You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. End with a firm decision and always conclude your response with 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**' to confirm your recommendation. Do not forget to utilize lessons from past decisions to learn from your mistakes. Here is some reflections from similar situations you traded in and the lessons learned: {past_memory_str}"""


TRADER_CONFIG = TraderConfig(
    name="trader",
    display_name="Trader",
    system_message=TRADER_SYSTEM_MESSAGE,
)


# Registry of all trader configurations
TRADER_CONFIGS = {
    "trader": TRADER_CONFIG,
}


def get_trader_config(trader_type: str) -> TraderConfig:
    """Get the configuration for a trader type.

    Args:
        trader_type: The type of trader (e.g., "trader")

    Returns:
        The trader configuration

    Raises:
        ValueError: If the trader type is not recognized
    """
    if trader_type not in TRADER_CONFIGS:
        available = ", ".join(TRADER_CONFIGS.keys())
        raise ValueError(
            f"Unknown trader type: {trader_type}. Available types: {available}"
        )
    return TRADER_CONFIGS[trader_type]
