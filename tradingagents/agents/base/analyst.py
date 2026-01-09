"""Base analyst class and factory for creating analyst agents."""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


# Common prompt template used by all analysts
COMMON_ANALYST_PROMPT = """You are a helpful AI assistant, collaborating with other assistants.
 Use the provided tools to progress towards answering the question.
 If you are unable to fully answer, that's OK; another assistant with different tools
 will help where you left off. Execute what you can to make progress.
 If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,
 prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop.
 You have access to the following tools: {tool_names}.\n{system_message}
For your reference, the current date is {current_date}. The company we want to look at is {ticker}"""


@dataclass
class AnalystConfig:
    """Configuration for an analyst agent.

    Attributes:
        name: The analyst's name (e.g., "market", "fundamentals")
        tools: List of tool functions the analyst can use
        system_message: The analyst's specialized system message
        report_field: The state field where the report is stored (e.g., "market_report")
        prompt_template: Optional custom prompt template
    """

    name: str
    tools: List[Callable]
    system_message: str
    report_field: str
    prompt_template: str = COMMON_ANALYST_PROMPT


class BaseAnalyst:
    """Base class for analyst agents.

    Provides common functionality for creating analyst node functions.
    """

    def __init__(self, llm, config: AnalystConfig):
        """Initialize the analyst.

        Args:
            llm: The language model to use
            config: The analyst configuration
        """
        self.llm = llm
        self.config = config

    def create_node(self) -> Callable:
        """Create the analyst node function.

        Returns:
            A function that can be used as a graph node
        """
        config = self.config
        llm = self.llm

        def analyst_node(state):
            current_date = state["trade_date"]
            ticker = state["company_of_interest"]

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", config.prompt_template),
                    MessagesPlaceholder(variable_name="messages"),
                ]
            )

            prompt = prompt.partial(system_message=config.system_message)
            prompt = prompt.partial(
                tool_names=", ".join([tool.name for tool in config.tools])
            )
            prompt = prompt.partial(current_date=current_date)
            prompt = prompt.partial(ticker=ticker)

            chain = prompt | llm.bind_tools(config.tools)
            result = chain.invoke(state["messages"])

            # Extract report if no tool calls (final response)
            report = ""
            if len(result.tool_calls) == 0:
                report = result.content

            return {
                "messages": [result],
                config.report_field: report,
            }

        return analyst_node


def create_analyst_from_config(llm, config: AnalystConfig) -> Callable:
    """Factory function to create an analyst node from configuration.

    Args:
        llm: The language model to use
        config: The analyst configuration

    Returns:
        A node function for the analyst
    """
    return BaseAnalyst(llm, config).create_node()
