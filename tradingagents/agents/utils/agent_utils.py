from langchain_core.messages import HumanMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_sentiment,
    get_insider_transactions,
    get_global_news
)

def create_msg_delete():
    def delete_messages(state):
        """Add placeholder for Anthropic compatibility.

        Note: We don't try to remove messages as it can fail when
        message IDs aren't in LangGraph's checkpoint state.
        """
        placeholder = HumanMessage(content="Continue")
        return {"messages": [placeholder]}

    return delete_messages


        