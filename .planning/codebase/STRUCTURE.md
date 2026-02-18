# Codebase Structure

**Analysis Date:** 2026-02-18

## Directory Layout

```
trading-agents/
├── tradingagents/          # Main package directory
│   ├── agents/            # Agent implementations and configurations
│   ├── backtesting/       # Backtesting engine (currently minimal)
│   ├── backtracking/      # Performance tracking and agent learning
│   ├── config/            # Configuration models (Pydantic)
│   ├── dataflows/         # Data retrieval with vendor abstraction
│   ├── graph/             # LangGraph workflow orchestration
│   ├── portfolio/         # Portfolio management integration
│   └── storage/           # Report storage backends
├── scripts/               # Utility scripts for scheduled analysis
├── tests/                 # Test suite (storage focus)
├── data/                  # Local data storage
├── reports/               # Generated trading reports
├── results/               # Backtesting results
├── eval_results/          # Agent evaluation logs
├── docs/                  # Documentation
├── assets/                # Static assets
└── .planning/             # GSD planning documents
```

## Directory Purposes

**tradingagents/agents:**
- Purpose: Core agent implementations and configurations
- Contains: Base agent classes (Analyst, Researcher, Debater, Manager, Trader), agent configurations, utility tools, state definitions, memory system
- Key files: `tradingagents/agents/base/analyst.py`, `tradingagents/agents/base/researcher.py`, `tradingagents/agents/utils/agent_states.py`, `tradingagents/agents/utils/memory.py`

**tradingagents/graph:**
- Purpose: LangGraph workflow orchestration
- Contains: TradingAgentsGraph main class, graph setup, conditional logic, propagation, reflection, signal processing
- Key files: `tradingagents/graph/trading_graph.py`, `tradingagents/graph/setup.py`, `tradingagents/graph/conditional_logic.py`

**tradingagents/dataflows:**
- Purpose: Financial data retrieval with vendor abstraction
- Contains: Vendor implementations (yfinance, Alpha Vantage, Google, Local, OpenAI), routing interface, caching, utility functions
- Key files: `tradingagents/dataflows/interface.py`, `tradingagents/dataflows/vendors/registry.py`, `tradingagents/dataflows/vendors/yfinance_vendor.py`, `tradingagents/dataflows/config.py`

**tradingagents/config:**
- Purpose: Centralized configuration management
- Contains: Pydantic configuration models for all system components
- Key files: `tradingagents/config/models.py`

**tradingagents/storage:**
- Purpose: Report storage with multiple backend support
- Contains: Storage service facade, backend implementations (local, R2), TL;DR generation, PDF conversion
- Key files: `tradingagents/storage/service.py`, `tradingagents/storage/base.py`, `tradingagents/storage/backends/local.py`, `tradingagents/storage/backends/r2.py`

**tradingagents/portfolio:**
- Purpose: Portfolio state management and Google Sheets integration
- Contains: GoogleSheetsPortfolio class, data models (Position, Transaction, PortfolioSummary)
- Key files: `tradingagents/portfolio/google_sheets.py`, `tradingagents/portfolio/models.py`

**tradingagents/backtracking:**
- Purpose: Agent performance tracking and reflection
- Contains: AgentTracker, PerformanceStorage, reflection utilities
- Key files: `tradingagents/backtracking/agent_tracker.py`, `tradingagents/backtracking/performance.py`, `tradingagents/backtracking/storage.py`

**scripts:**
- Purpose: Utility scripts for automation
- Contains: Scheduled analysis runner for GitHub Actions, report upload utilities
- Key files: `scripts/run_scheduled_analysis.py`, `scripts/upload_existing_reports.py`

**tests:**
- Purpose: Test suite (currently focused on storage)
- Contains: Storage service tests, backend tests, configuration tests
- Key files: `tests/storage/test_service.py`, `tests/storage/test_local_backend.py`, `tests/storage/test_r2_backend.py`

## Key File Locations

**Entry Points:**
- `tradingagents/graph/trading_graph.py`: Main TradingAgentsGraph class with propagate() method
- `scripts/run_scheduled_analysis.py`: Batch analysis script for CI/CD
- `setup.py`: Package installation with CLI entry point definition

**Configuration:**
- `tradingagents/config/models.py`: Pydantic configuration models (TradingAgentsConfig, LLMConfig, etc.)
- `tradingagents/default_config.py`: Default configuration constants
- `.env`: Environment variables for secrets and API keys (not in git)

**Core Logic:**
- `tradingagents/agents/base/`: All agent base classes and factory functions
- `tradingagents/graph/setup.py`: LangGraph workflow construction
- `tradingagents/dataflows/interface.py`: Vendor routing and data retrieval

**Testing:**
- `tests/storage/`: Storage backend and service tests
- `tests/__init__.py`: Test package initialization

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (e.g., `trading_graph.py`, `agent_states.py`)
- Test files: `test_<module>.py` (e.g., `test_service.py`)
- Config files: `snake_case.py` (e.g., `models.py`, `default_config.py`)

**Directories:**
- Package directories: `snake_case` (e.g., `dataflows`, `backtracking`)
- Test directories: `tests/` matching package structure

**Classes:**
- Agent classes: `PascalCase` with descriptive names (e.g., `TradingAgentsGraph`, `BaseAnalyst`, `YFinanceVendor`)
- Configuration classes: `PascalCase` with `Config` suffix (e.g., `LLMConfig`, `TradingAgentsConfig`)
- State classes: `PascalCase` with `State` suffix (e.g., `AgentState`, `InvestDebateState`)

**Functions:**
- Public functions: `snake_case` (e.g., `propagate()`, `route_to_vendor()`)
- Factory functions: `create_<type>_from_config` (e.g., `create_analyst_from_config`)
- Private functions: `_snake_case` prefix

**Constants:**
- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONFIG`, `CACHE_TTL`)
- Configuration keys: `snake_case` (e.g., `deep_think_llm`, `backend_url`)

## Where to Add New Code

**New Agent Type:**
- Primary code: `tradingagents/agents/base/<agent_type>.py`
- Configuration: `tradingagents/agents/base/<agent_type>_configs.py`
- Exports: Add to `tradingagents/agents/base/__init__.py`
- Integration: Add node setup in `tradingagents/graph/setup.py`

**New Data Vendor:**
- Implementation: `tradingagents/dataflows/vendors/<vendor>_vendor.py`
- Registration: Add to `_initialize_default_vendors()` in `tradingagents/dataflows/vendors/registry.py`
- Tests: Create vendor-specific test in `tests/dataflows/` (when test suite expands)

**New Storage Backend:**
- Implementation: `tradingagents/storage/backends/<backend>.py`
- Import in service: Add to `tradingagents/storage/service.py`
- Tests: `tests/storage/test_<backend>_backend.py`

**New Agent Tool:**
- Tool function: `tradingagents/agents/utils/<category>_tools.py`
- Abstract interface: Add to `tradingagents/agents/utils/agent_utils.py`
- Vendor implementations: Implement in `tradingagents/dataflows/vendors/<vendor>_vendor.py`
- Tool node: Add to `_create_tool_nodes()` in `tradingagents/graph/trading_graph.py`

**New Configuration Option:**
- Add field to relevant Pydantic model in `tradingagents/config/models.py`
- Update `to_legacy_dict()` and `from_legacy_dict()` for backward compatibility
- Document in `.env.example`

**Utilities:**
- Shared helpers: `tradingagents/agents/utils/` for agent-related utilities
- Data utilities: `tradingagents/dataflows/utils.py` for data processing

## Special Directories

**.planning/:**
- Purpose: GSD (Generate Software Design) planning documents
- Generated: Yes - by GSD commands
- Committed: Yes

**data/ and dataflows/data_cache/:**
- Purpose: Local caching of retrieved financial data
- Generated: Yes - by data retrieval operations
- Committed: No (gitignored)

**reports/ and results/ and eval_results/:**
- Purpose: Generated trading reports, backtesting results, agent evaluation logs
- Generated: Yes - by analysis execution
- Committed: No (gitignored)

**.venv/:**
- Purpose: Python virtual environment
- Generated: Yes - by Python/virtualenv tools
- Committed: No (gitignored)

**__pycache__/ within tradingagents/:**
- Purpose: Python bytecode cache
- Generated: Yes - by Python interpreter
- Committed: No (gitignored)

**tradingagents.egg-info/:**
- Purpose: Package metadata from installation
- Generated: Yes - by setup.py/pip
- Committed: No (gitignored)

---

*Structure analysis: 2026-02-18*
