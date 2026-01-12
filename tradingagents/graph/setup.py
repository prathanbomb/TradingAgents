# TradingAgents/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import create_msg_delete
from tradingagents.agents.base import (
    create_analyst_from_config,
    get_analyst_config,
    create_researcher_from_config,
    BULL_RESEARCHER_CONFIG,
    BEAR_RESEARCHER_CONFIG,
    create_debater_from_config,
    RISKY_DEBATER_CONFIG,
    SAFE_DEBATER_CONFIG,
    NEUTRAL_DEBATER_CONFIG,
    create_manager_from_config,
    RESEARCH_MANAGER_CONFIG,
    RISK_MANAGER_CONFIG,
    create_trader_from_config,
    TRADER_CONFIG,
)
from tradingagents.agents.base.portfolio_manager import (
    create_portfolio_manager_from_config,
)
from tradingagents.agents.base.portfolio_manager_configs import (
    PORTFOLIO_MANAGER_CONFIG,
)
from tradingagents.agents.utils.agent_states import AgentState

from .conditional_logic import ConditionalLogic
from .propagation import analyst_collector_node


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
        portfolio_manager_memory=None,
        portfolio_service=None,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.portfolio_manager_memory = portfolio_manager_memory
        self.portfolio_service = portfolio_service
        self.conditional_logic = conditional_logic

    def setup_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals"]
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        # Create analyst nodes using base class factory
        for analyst_type in selected_analysts:
            config = get_analyst_config(analyst_type)
            analyst_nodes[analyst_type] = create_analyst_from_config(
                self.quick_thinking_llm, config
            )
            delete_nodes[analyst_type] = create_msg_delete()
            tool_nodes[analyst_type] = self.tool_nodes[analyst_type]

        # Create researcher nodes using base class factory
        bull_researcher_node = create_researcher_from_config(
            self.quick_thinking_llm, self.bull_memory, BULL_RESEARCHER_CONFIG
        )
        bear_researcher_node = create_researcher_from_config(
            self.quick_thinking_llm, self.bear_memory, BEAR_RESEARCHER_CONFIG
        )

        # Create manager and trader nodes using base class factory
        research_manager_node = create_manager_from_config(
            self.deep_thinking_llm, self.invest_judge_memory, RESEARCH_MANAGER_CONFIG
        )
        trader_node = create_trader_from_config(
            self.quick_thinking_llm, self.trader_memory, TRADER_CONFIG
        )

        # Create risk debater nodes using base class factory
        risky_analyst = create_debater_from_config(
            self.quick_thinking_llm, RISKY_DEBATER_CONFIG
        )
        safe_analyst = create_debater_from_config(
            self.quick_thinking_llm, SAFE_DEBATER_CONFIG
        )
        neutral_analyst = create_debater_from_config(
            self.quick_thinking_llm, NEUTRAL_DEBATER_CONFIG
        )
        risk_manager_node = create_manager_from_config(
            self.deep_thinking_llm, self.risk_manager_memory, RISK_MANAGER_CONFIG
        )

        # Create portfolio manager node if enabled
        portfolio_manager_node = None
        if self.portfolio_service:
            portfolio_manager_node = create_portfolio_manager_from_config(
                self.deep_thinking_llm,
                self.portfolio_manager_memory or self.invest_judge_memory,
                PORTFOLIO_MANAGER_CONFIG,
                self.portfolio_service,
            )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        # Add portfolio manager node if enabled
        if portfolio_manager_node:
            workflow.add_node("Portfolio Manager", portfolio_manager_node)

        # Add collector node for parallel analyst execution
        workflow.add_node("Analyst Collector", analyst_collector_node)

        # Define edges - Parallel analyst execution
        # Fan-out: START -> all analysts simultaneously
        for analyst_type in selected_analysts:
            workflow.add_edge(START, f"{analyst_type.capitalize()} Analyst")

        # Set up each analyst's tool loop and fan-in to collector
        for analyst_type in selected_analysts:
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # Add conditional edges for current analyst's tool loop
            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

            # Fan-in: all analysts -> Collector
            workflow.add_edge(current_clear, "Analyst Collector")

        # Collector proceeds to debate phase
        workflow.add_edge("Analyst Collector", "Bull Researcher")

        # Add remaining edges
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Risky Analyst")
        workflow.add_conditional_edges(
            "Risky Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Safe Analyst": "Safe Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Safe Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Risky Analyst": "Risky Analyst",
                "Risk Judge": "Risk Judge",
            },
        )

        # Risk Judge goes to Portfolio Manager (if enabled) or END
        if portfolio_manager_node:
            workflow.add_edge("Risk Judge", "Portfolio Manager")
            workflow.add_edge("Portfolio Manager", END)
        else:
            workflow.add_edge("Risk Judge", END)

        # Compile and return
        return workflow.compile()
