# TradingAgents/graph/trading_graph.py

import logging
import os
from pathlib import Path
import json
from datetime import date
from typing import Dict, Any, Tuple, List, Optional, Union
import asyncio
import uuid

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.config import TradingAgentsConfig
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.config import set_config

# Import the new abstract tool methods from agent_utils
from tradingagents.agents.utils.agent_utils import (
    get_stock_data,
    get_indicators,
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_news,
    get_insider_sentiment,
    get_insider_transactions,
    get_global_news
)

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor

# Observability imports (optional, for decision tracking)
from tradingagents.observability.instrumentation import create_observation_run
from tradingagents.observability.pipeline import create_pipeline


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Union[TradingAgentsConfig, Dict[str, Any], None] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration (TradingAgentsConfig or legacy dict). If None, uses default.
        """
        self.debug = debug

        # Handle both new and legacy config formats
        if config is None:
            self._config = TradingAgentsConfig()
        elif isinstance(config, TradingAgentsConfig):
            self._config = config
        else:
            # Legacy dictionary format
            self._config = TradingAgentsConfig.from_legacy_dict(config)

        # Legacy dict for backward compatibility with existing code
        self.config = self._config.to_legacy_dict()

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs
        provider = self.config["llm_provider"].lower()
        logger.info(f"Initializing LLM provider: {provider}")

        if provider in ["openai", "ollama", "openrouter", "openai-compatible"]:
            # Get API key from configured env var (defaults to OPENAI_API_KEY)
            api_key_env = self.config.get("api_key_env_var", "OPENAI_API_KEY")

            # Check if it's a direct key (from CLI) or env var name
            if api_key_env.startswith("__DIRECT_KEY__:"):
                api_key = api_key_env.replace("__DIRECT_KEY__:", "")
            else:
                api_key = os.environ.get(api_key_env)

            if not api_key:
                raise ValueError(
                    f"API key not found. Please set the '{api_key_env}' environment variable "
                    f"or provide the key directly when prompted."
                )

            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"],
                base_url=self.config["backend_url"],
                api_key=api_key
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"],
                base_url=self.config["backend_url"],
                api_key=api_key
            )
        elif provider == "anthropic":
            self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif provider == "google":
            self.deep_thinking_llm = ChatGoogleGenerativeAI(model=self.config["deep_think_llm"])
            self.quick_thinking_llm = ChatGoogleGenerativeAI(model=self.config["quick_think_llm"])
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config['llm_provider']}")
        
        # Initialize memories
        logger.debug("Initializing memory systems")
        self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
        self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
        self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)
        self.portfolio_manager_memory = FinancialSituationMemory("portfolio_manager_memory", self.config)

        # Initialize portfolio service if configured
        self.portfolio_service = None
        if self._config.portfolio_manager.is_configured:
            try:
                from tradingagents.portfolio import GoogleSheetsPortfolio
                gs_config = self._config.portfolio_manager.google_sheets
                self.portfolio_service = GoogleSheetsPortfolio(
                    sheet_id=gs_config.sheet_id,
                    credentials_path=gs_config.credentials_path,
                    sheet_name=gs_config.sheet_name,
                )
                # Initialize the spreadsheet with headers if needed
                self.portfolio_service.initialize_sheets()
                logger.info("Portfolio Manager enabled with Google Sheets")
            except Exception as e:
                logger.warning(f"Failed to initialize portfolio service: {e}")

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic()
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
            self.portfolio_manager_memory,
            self.portfolio_service,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Initialize observability if enabled
        self.observability_pipeline = None
        self.observability_enabled = self._config.observability.enabled

        if self.observability_enabled:
            logger.info("Observability enabled, initializing data collection pipeline")
            # Note: Pipeline is started lazily to avoid blocking __init__
            self._observability_initialized = False
        else:
            self._observability_initialized = False

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)
        logger.info(f"Graph initialized with analysts: {selected_analysts}")

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources using abstract methods."""
        return {
            "market": ToolNode(
                [
                    # Core stock data tools
                    get_stock_data,
                    # Technical indicators
                    get_indicators,
                ]
            ),
            "social": ToolNode(
                [
                    # News tools for social media analysis
                    get_news,
                ]
            ),
            "news": ToolNode(
                [
                    # News and insider information
                    get_news,
                    get_global_news,
                    get_insider_sentiment,
                    get_insider_transactions,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    # Fundamental analysis tools
                    get_fundamentals,
                    get_balance_sheet,
                    get_cashflow,
                    get_income_statement,
                ]
            ),
        }

    async def _ensure_observability_initialized(self):
        """Lazily initialize observability pipeline."""
        if self.observability_enabled and not self._observability_initialized:
            db_path = self._config.observability.db_path
            self.observability_pipeline = await create_pipeline(
                db_path=str(db_path),
                max_queue_size=self._config.observability.max_queue_size,
                batch_size=self._config.observability.batch_size,
                auto_start=True
            )
            self._observability_initialized = True
            logger.info(f"Observability pipeline initialized: {db_path}")

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""
        logger.info(f"Starting analysis for {company_name} on {trade_date}")

        self.ticker = company_name

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        args = self.propagator.get_graph_args()

        # Create observation run if enabled
        collector = None
        extractor = None
        run_id = None
        if self.observability_enabled:
            run_id, collector, extractor = create_observation_run(company_name)
            logger.debug(f"Created observation run: {run_id}")

        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            in_async_context = True
        except RuntimeError:
            in_async_context = False

        # Create async task for observability if enabled and in async context
        observability_task = None
        if self.observability_enabled and in_async_context and collector:
            # Schedule async event capture without blocking
            observability_task = asyncio.create_task(
                self._capture_observability_async(collector, extractor, init_agent_state, args, run_id)
            )

        if self.debug:
            # Debug mode with tracing
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                if len(chunk["messages"]) == 0:
                    pass
                else:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)

            final_state = trace[-1]
        else:
            # Standard mode without tracing
            final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        # Process and return decision
        decision = self.process_signal(final_state["final_trade_decision"])
        logger.info(f"Analysis completed for {company_name}: {decision}")

        # Capture observability data if enabled (sync fallback)
        if self.observability_enabled and not in_async_context:
            # Not in async context, do sync capture
            self._capture_observability_sync(extractor, final_state, company_name, trade_date, run_id)

        return final_state, decision

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "risky_history": final_state["risk_debate_state"]["risky_history"],
                "safe_history": final_state["risk_debate_state"]["safe_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
            "personalized_recommendation": final_state.get("personalized_recommendation", ""),
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )
        self.reflector.reflect_portfolio_manager(
            self.curr_state, returns_losses, self.portfolio_manager_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)

    async def _capture_observability_async(self, collector, extractor, init_state, args, run_id):
        """Capture observability data asynchronously during graph execution.

        This method runs as a background task to capture events without blocking
        the trading pipeline.
        """
        await self._ensure_observability_initialized()

        # Stream events and capture decisions
        events_collected = []
        try:
            async for event in collector.collect_events(self.graph, init_state, config=args.get("config", {})):
                events_collected.append(event)
                # Non-blocking enqueue
                if self.observability_pipeline:
                    await self.observability_pipeline.producer(event)
        except Exception as e:
            logger.warning(f"Async event capture failed: {e}")

        # Extract decision records from final state (after graph completes)
        final_state = self.curr_state  # Set by propagate()
        if final_state and extractor:
            try:
                records = extractor.extract_decision_records(
                    final_state, self.ticker, final_state.get("trade_date", ""), run_id
                )
                for record in records:
                    await self.observability_pipeline.producer(record)
                logger.debug(f"Captured {len(records)} decision records for {self.ticker}")
            except Exception as e:
                logger.warning(f"Decision record extraction failed: {e}")

    def _capture_observability_sync(self, extractor, final_state, ticker, trade_date, run_id):
        """Capture observability data synchronously (fallback for non-async contexts).

        This method is used when not in an async event loop. It stores decisions
        directly without the async pipeline.
        """
        if not extractor:
            return

        try:
            # Extract decision records from final state
            records = extractor.extract_decision_records(
                final_state, ticker, trade_date, run_id or str(uuid.uuid4())
            )

            if records:
                # Store directly using SQLite backend (simpler path for non-async contexts)
                from tradingagents.observability.storage import SQLiteDecisionStore
                store = SQLiteDecisionStore(str(self._config.observability.db_path))

                # Try async first if loop is running
                try:
                    loop = asyncio.get_running_loop()
                    # Create task for non-blocking store
                    asyncio.create_task(store.store_batch(records))
                except RuntimeError:
                    # No loop running, run synchronously
                    import asyncio
                    asyncio.run(store.store_batch(records))

                logger.debug(f"Captured {len(records)} decision records for {ticker}")
        except Exception as e:
            logger.warning(f"Sync observability capture failed: {e}")

    async def shutdown_observability(self):
        """Gracefully shutdown observability pipeline.

        Call this before destroying the TradingAgentsGraph instance to ensure
        all pending observability data is flushed.
        """
        if self.observability_pipeline:
            await self.observability_pipeline.stop()
            logger.info("Observability pipeline shutdown complete")
