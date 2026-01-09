# TradingAgents/graph/conditional_logic.py

from tradingagents.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

        # Generate analyst router methods dynamically
        for analyst_type in ["market", "social", "news", "fundamentals"]:
            setattr(self, f"should_continue_{analyst_type}",
                    self._create_analyst_router(analyst_type))

    def _create_analyst_router(self, analyst_type: str):
        """Create a router function for the given analyst type."""
        tools_key = f"tools_{analyst_type}"
        clear_key = f"Msg Clear {analyst_type.capitalize()}"

        def router(state: AgentState):
            if state["messages"][-1].tool_calls:
                return tools_key
            return clear_key

        router.__doc__ = f"Determine if {analyst_type} analysis should continue."
        return router

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""

        if (
            state["investment_debate_state"]["count"] >= 2 * self.max_debate_rounds
        ):  # 3 rounds of back-and-forth between 2 agents
            return "Research Manager"
        if state["investment_debate_state"]["current_response"].startswith("Bull"):
            return "Bear Researcher"
        return "Bull Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        if (
            state["risk_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds
        ):  # 3 rounds of back-and-forth between 3 agents
            return "Risk Judge"
        if state["risk_debate_state"]["latest_speaker"].startswith("Risky"):
            return "Safe Analyst"
        if state["risk_debate_state"]["latest_speaker"].startswith("Safe"):
            return "Neutral Analyst"
        return "Risky Analyst"
