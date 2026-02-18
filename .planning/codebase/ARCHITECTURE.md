# Architecture

**Analysis Date:** 2026-02-18

## Pattern Overview

**Overall:** Multi-Agent LLM Trading System with LangGraph

**Key Characteristics:**
- Multi-agent architecture with specialized roles (analysts, researchers, debaters, managers, traders)
- LangGraph-based state machine workflow for agent orchestration
- Vendor abstraction layer for multi-source data retrieval
- Memory-backed reflection system for agent learning
- Modular storage backend with local and cloud (R2) support

## Layers

**Agent Layer:**
- Purpose: Implements intelligent agents that analyze financial data and make trading decisions
- Location: `tradingagents/agents/`
- Contains: Base agent classes (Analyst, Researcher, Debater, Manager, Trader), configuration objects, utility tools
- Depends on: LangChain/LangGraph for LLM orchestration, dataflows for financial data, memory for persistence
- Used by: Graph layer for workflow orchestration

**Graph Orchestration Layer:**
- Purpose: Coordinates agent interactions through state machine workflows
- Location: `tradingagents/graph/`
- Contains: TradingAgentsGraph (main orchestrator), GraphSetup (workflow builder), conditional logic, propagation, reflection, signal processing
- Depends on: Agent layer, state management (AgentState), LangGraph StateGraph
- Used by: CLI, scripts, backtesting module

**Data Flow Layer:**
- Purpose: Retrieves financial data from multiple sources with vendor abstraction and fallback
- Location: `tradingagents/dataflows/`
- Contains: Vendor implementations, routing interface, caching, data persistence
- Depends on: External APIs (yfinance, Alpha Vantage, Google), local file system
- Used by: Agent tools for data retrieval

**Configuration Layer:**
- Purpose: Centralized configuration management with Pydantic models
- Location: `tradingagents/config/`
- Contains: TradingAgentsConfig, LLMConfig, DataVendorConfig, StorageConfig, PathConfig
- Depends on: Pydantic for validation
- Used by: All layers for configuration access

**Storage Layer:**
- Purpose: Unified report storage with multiple backend support (local filesystem, Cloudflare R2)
- Location: `tradingagents/storage/`
- Contains: StorageService facade, backend implementations (local, R2), TL;DR generation, PDF conversion
- Depends on: boto3 (for R2), weasyprint (for PDF), file system
- Used by: Scripts, reporting pipeline

**Portfolio Management Layer:**
- Purpose: Tracks portfolio state and provides context-aware recommendations
- Location: `tradingagents/portfolio/`
- Contains: GoogleSheetsPortfolio integration, Position/Transaction models
- Depends on: Google Sheets API
- Used by: Portfolio Manager agent

**Backtracking Layer:**
- Purpose: Tracks agent decisions and performance for learning and evaluation
- Location: `tradingagents/backtracking/`
- Contains: AgentTracker, PerformanceStorage, reflection utilities
- Depends on: File system, JSON storage
- Used by: Reflection system, evaluation scripts

## Data Flow

**Trading Analysis Execution:**

1. TradingAgentsGraph initialized with config, LLMs, memories, tool nodes
2. propagate() called with company_name and trade_date
3. Initial AgentState created with company/date context
4. LangGraph workflow executes:
   - Parallel analyst execution (Market, Social, News, Fundamentals)
   - Each analyst uses tool nodes to fetch data via vendor routing
   - Analyst reports collected in state
   - Bull/Bear researchers debate based on analyst reports
   - Research Manager judges debate and creates investment plan
   - Trader creates detailed investment plan
   - Risk/Safe/Neutral analysts debate risk
   - Risk Judge makes final decision
   - Portfolio Manager provides personalized recommendation (if enabled)
5. Final state logged to JSON
6. Decision processed and returned
7. reflect_and_remember() updates memories based on returns

**Data Retrieval Flow:**

1. Agent tool calls abstract method (e.g., get_stock_data)
2. Data interface routes to configured vendor via VendorRegistry
3. Vendor implementation fetches from external API or local cache
4. Result cached in TTL cache (5 minutes)
5. On vendor failure, automatic fallback to next available vendor
6. Data saved to local cache for persistence

**State Management:**
- AgentState (TypedDict) flows through LangGraph nodes
- Nested state objects: InvestDebateState, RiskDebateState
- Reducers handle nested state updates (replace_value function)
- MessagesState extension for LLM message history

## Key Abstractions

**Agent Base Classes:**
- Purpose: Polymorphic agent creation with factory pattern
- Examples: `tradingagents/agents/base/analyst.py`, `tradingagents/agents/base/researcher.py`, `tradingagents/agents/base/debater.py`, `tradingagents/agents/base/manager.py`, `tradingagents/agents/base/trader.py`
- Pattern: Config-based factory functions (create_X_from_config) returning LangGraph nodes

**Vendor Registry:**
- Purpose: Dynamic routing of data requests to multiple vendor implementations
- Examples: `tradingagents/dataflows/vendors/registry.py`, `tradingagents/dataflows/vendors/yfinance_vendor.py`, `tradingagents/dataflows/vendors/alpha_vantage_vendor.py`
- Pattern: Registry pattern with VendorRegistry singleton, BaseVendor protocol

**Storage Backend:**
- Purpose: Abstract storage operations across local filesystem and cloud storage
- Examples: `tradingagents/storage/base.py`, `tradingagents/storage/backends/local.py`, `tradingagents/storage/backends/r2.py`
- Pattern: Protocol-based interface (StorageBackend) with facade (StorageService)

**Memory System:**
- Purpose: Persistent context for agents across trading sessions
- Examples: `tradingagents/agents/utils/memory.py`
- Pattern: ChromaDB-backed vector store with financial situation embeddings

## Entry Points

**TradingAgentsGraph.propagate():**
- Location: `tradingagents/graph/trading_graph.py`
- Triggers: Manual trading analysis requests, scheduled scripts, backtesting
- Responsibilities: Orchestrates full multi-agent analysis workflow for a single ticker/date

**CLI (not found - referenced in setup.py):**
- Location: `cli.main:app` (external to tradingagents package)
- Triggers: User commands
- Responsibilities: Interactive command-line interface for running analyses

**run_scheduled_analysis.py:**
- Location: `scripts/run_scheduled_analysis.py`
- Triggers: GitHub Actions cron, manual execution
- Responsibilities: Batch analysis of tickers from tickers.txt, report generation and storage

**TradingAgentsGraph.__init__():**
- Location: `tradingagents/graph/trading_graph.py`
- Triggers: Application startup
- Responsibilities: Initializes all agents, LLMs, memories, and builds LangGraph workflow

## Error Handling

**Strategy:** Graceful degradation with fallback

**Patterns:**
- Vendor-level fallback: If primary vendor fails, automatically tries next available vendor
- Rate limiting: AlphaVantageRateLimitError triggers fallback
- Configuration validation: Pydantic validators ensure valid config at initialization
- Optional features: PDF conversion, portfolio manager gracefully degrade if unavailable
- Logging: Comprehensive logging at all levels for debugging

## Cross-Cutting Concerns

**Logging:** Python logging module with structured logging throughout all layers

**Validation:** Pydantic models for configuration, TypedDict for state validation

**Authentication:** API keys via environment variables, provider-specific auth (OpenAI, Anthropic, Google)

**Caching:** TTL cache for vendor requests (5 minutes), local file cache for persisted data

**Configuration:** Centralized TradingAgentsConfig with legacy dict compatibility

**Memory:** ChromaDB vector embeddings for agent learning (can be disabled)

---

*Architecture analysis: 2026-02-18*
