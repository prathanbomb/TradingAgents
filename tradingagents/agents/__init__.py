"""Trading agents module - all agents are now config-driven via base classes."""

from .utils.agent_utils import create_msg_delete
from .utils.agent_states import AgentState, InvestDebateState, RiskDebateState
from .utils.memory import FinancialSituationMemory

# All agent factories and configs from base module
from .base import (
    # Analyst
    create_analyst_from_config,
    get_analyst_config,
    MARKET_ANALYST_CONFIG,
    FUNDAMENTALS_ANALYST_CONFIG,
    NEWS_ANALYST_CONFIG,
    SOCIAL_ANALYST_CONFIG,
    # Researcher
    create_researcher_from_config,
    get_researcher_config,
    BULL_RESEARCHER_CONFIG,
    BEAR_RESEARCHER_CONFIG,
    # Debater
    create_debater_from_config,
    get_debater_config,
    RISKY_DEBATER_CONFIG,
    SAFE_DEBATER_CONFIG,
    NEUTRAL_DEBATER_CONFIG,
    # Manager
    create_manager_from_config,
    get_manager_config,
    RESEARCH_MANAGER_CONFIG,
    RISK_MANAGER_CONFIG,
    # Trader
    create_trader_from_config,
    get_trader_config,
    TRADER_CONFIG,
)

__all__ = [
    # Utils
    "FinancialSituationMemory",
    "AgentState",
    "InvestDebateState",
    "RiskDebateState",
    "create_msg_delete",
    # Analyst
    "create_analyst_from_config",
    "get_analyst_config",
    "MARKET_ANALYST_CONFIG",
    "FUNDAMENTALS_ANALYST_CONFIG",
    "NEWS_ANALYST_CONFIG",
    "SOCIAL_ANALYST_CONFIG",
    # Researcher
    "create_researcher_from_config",
    "get_researcher_config",
    "BULL_RESEARCHER_CONFIG",
    "BEAR_RESEARCHER_CONFIG",
    # Debater
    "create_debater_from_config",
    "get_debater_config",
    "RISKY_DEBATER_CONFIG",
    "SAFE_DEBATER_CONFIG",
    "NEUTRAL_DEBATER_CONFIG",
    # Manager
    "create_manager_from_config",
    "get_manager_config",
    "RESEARCH_MANAGER_CONFIG",
    "RISK_MANAGER_CONFIG",
    # Trader
    "create_trader_from_config",
    "get_trader_config",
    "TRADER_CONFIG",
]
