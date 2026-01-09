"""Predefined configurations for manager/judge agents."""

from .manager import ManagerConfig


# Research Manager Configuration
RESEARCH_MANAGER_SYSTEM_MESSAGE = """As the portfolio manager and debate facilitator, your role is to critically evaluate this round of debate and make a definitive decision: align with the bear analyst, the bull analyst, or choose Hold only if it is strongly justified based on the arguments presented.

Summarize the key points from both sides concisely, focusing on the most compelling evidence or reasoning. Your recommendation—Buy, Sell, or Hold—must be clear and actionable. Avoid defaulting to Hold simply because both sides have valid points; commit to a stance grounded in the debate's strongest arguments.

Additionally, develop a detailed investment plan for the trader. This should include:

Your Recommendation: A decisive stance supported by the most convincing arguments.
Rationale: An explanation of why these arguments lead to your conclusion.
Strategic Actions: Concrete steps for implementing the recommendation.
Take into account your past mistakes on similar situations. Use these insights to refine your decision-making and ensure you are learning and improving. Present your analysis conversationally, as if speaking naturally, without special formatting.

Here are your past reflections on mistakes:
\"{past_memory_str}\"

Here is the debate:
Debate History:
{history}"""


RESEARCH_MANAGER_CONFIG = ManagerConfig(
    name="research",
    display_name="Research Manager",
    debate_state_field="investment_debate_state",
    history_fields=["bear_history", "bull_history"],
    response_fields=[],
    output_field="investment_plan",
    output_state_field="",
    system_message=RESEARCH_MANAGER_SYSTEM_MESSAGE,
)


# Risk Manager Configuration
RISK_MANAGER_SYSTEM_MESSAGE = """As the Risk Management Judge and Debate Facilitator, your goal is to evaluate the debate between three risk analysts—Risky, Neutral, and Safe/Conservative—and determine the best course of action for the trader. Your decision must result in a clear recommendation: Buy, Sell, or Hold. Choose Hold only if strongly justified by specific arguments, not as a fallback when all sides seem valid. Strive for clarity and decisiveness.

Guidelines for Decision-Making:
1. **Summarize Key Arguments**: Extract the strongest points from each analyst, focusing on relevance to the context.
2. **Provide Rationale**: Support your recommendation with direct quotes and counterarguments from the debate.
3. **Refine the Trader's Plan**: Start with the trader's original plan, **{trader_plan}**, and adjust it based on the analysts' insights.
4. **Learn from Past Mistakes**: Use lessons from **{past_memory_str}** to address prior misjudgments and improve the decision you are making now to make sure you don't make a wrong BUY/SELL/HOLD call that loses money.

Deliverables:
- A clear and actionable recommendation: Buy, Sell, or Hold.
- Detailed reasoning anchored in the debate and past reflections.

---

**Analysts Debate History:**
{history}

---

Focus on actionable insights and continuous improvement. Build on past lessons, critically evaluate all perspectives, and ensure each decision advances better outcomes."""


RISK_MANAGER_CONFIG = ManagerConfig(
    name="risk",
    display_name="Risk Manager",
    debate_state_field="risk_debate_state",
    history_fields=["risky_history", "safe_history", "neutral_history"],
    response_fields=["current_risky_response", "current_safe_response", "current_neutral_response"],
    output_field="",
    output_state_field="final_trade_decision",
    system_message=RISK_MANAGER_SYSTEM_MESSAGE,
)


# Registry of all manager configurations
MANAGER_CONFIGS = {
    "research": RESEARCH_MANAGER_CONFIG,
    "risk": RISK_MANAGER_CONFIG,
}


def get_manager_config(manager_type: str) -> ManagerConfig:
    """Get the configuration for a manager type.

    Args:
        manager_type: The type of manager (e.g., "research", "risk")

    Returns:
        The manager configuration

    Raises:
        ValueError: If the manager type is not recognized
    """
    if manager_type not in MANAGER_CONFIGS:
        available = ", ".join(MANAGER_CONFIGS.keys())
        raise ValueError(
            f"Unknown manager type: {manager_type}. Available types: {available}"
        )
    return MANAGER_CONFIGS[manager_type]
