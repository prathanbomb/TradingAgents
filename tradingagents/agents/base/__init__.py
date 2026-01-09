"""Base classes and factories for agent creation."""

from .analyst import (
    AnalystConfig,
    BaseAnalyst,
    create_analyst_from_config,
    COMMON_ANALYST_PROMPT,
)
from .analyst_configs import (
    ANALYST_CONFIGS,
    MARKET_ANALYST_CONFIG,
    FUNDAMENTALS_ANALYST_CONFIG,
    NEWS_ANALYST_CONFIG,
    SOCIAL_ANALYST_CONFIG,
    get_analyst_config,
)
from .researcher import (
    ResearcherConfig,
    BaseResearcher,
    create_researcher_from_config,
)
from .researcher_configs import (
    RESEARCHER_CONFIGS,
    BULL_RESEARCHER_CONFIG,
    BEAR_RESEARCHER_CONFIG,
    get_researcher_config,
)
from .debater import (
    DebaterConfig,
    BaseDebater,
    create_debater_from_config,
)
from .debater_configs import (
    DEBATER_CONFIGS,
    RISKY_DEBATER_CONFIG,
    SAFE_DEBATER_CONFIG,
    NEUTRAL_DEBATER_CONFIG,
    get_debater_config,
)
from .manager import (
    ManagerConfig,
    BaseManager,
    create_manager_from_config,
)
from .manager_configs import (
    MANAGER_CONFIGS,
    RESEARCH_MANAGER_CONFIG,
    RISK_MANAGER_CONFIG,
    get_manager_config,
)
from .trader import (
    TraderConfig,
    BaseTrader,
    create_trader_from_config,
)
from .trader_configs import (
    TRADER_CONFIGS,
    TRADER_CONFIG,
    get_trader_config,
)

__all__ = [
    # Analyst base classes
    "AnalystConfig",
    "BaseAnalyst",
    "create_analyst_from_config",
    "COMMON_ANALYST_PROMPT",
    # Analyst configurations
    "ANALYST_CONFIGS",
    "MARKET_ANALYST_CONFIG",
    "FUNDAMENTALS_ANALYST_CONFIG",
    "NEWS_ANALYST_CONFIG",
    "SOCIAL_ANALYST_CONFIG",
    "get_analyst_config",
    # Researcher base classes
    "ResearcherConfig",
    "BaseResearcher",
    "create_researcher_from_config",
    # Researcher configurations
    "RESEARCHER_CONFIGS",
    "BULL_RESEARCHER_CONFIG",
    "BEAR_RESEARCHER_CONFIG",
    "get_researcher_config",
    # Debater base classes
    "DebaterConfig",
    "BaseDebater",
    "create_debater_from_config",
    # Debater configurations
    "DEBATER_CONFIGS",
    "RISKY_DEBATER_CONFIG",
    "SAFE_DEBATER_CONFIG",
    "NEUTRAL_DEBATER_CONFIG",
    "get_debater_config",
    # Manager base classes
    "ManagerConfig",
    "BaseManager",
    "create_manager_from_config",
    # Manager configurations
    "MANAGER_CONFIGS",
    "RESEARCH_MANAGER_CONFIG",
    "RISK_MANAGER_CONFIG",
    "get_manager_config",
    # Trader base classes
    "TraderConfig",
    "BaseTrader",
    "create_trader_from_config",
    # Trader configurations
    "TRADER_CONFIGS",
    "TRADER_CONFIG",
    "get_trader_config",
]
