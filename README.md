<p align="center">
  <img src="assets/TauricResearch.png" style="width: 60%; height: auto;">
</p>

<div align="center" style="line-height: 1;">
  <a href="https://arxiv.org/abs/2412.20138" target="_blank"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2412.20138-B31B1B?logo=arxiv"/></a>
  <a href="https://discord.com/invite/hk9PGKShPK" target="_blank"><img alt="Discord" src="https://img.shields.io/badge/Discord-TradingResearch-7289da?logo=discord&logoColor=white&color=7289da"/></a>
  <a href="./assets/wechat.png" target="_blank"><img alt="WeChat" src="https://img.shields.io/badge/WeChat-TauricResearch-brightgreen?logo=wechat&logoColor=white"/></a>
  <a href="https://x.com/TauricResearch" target="_blank"><img alt="X Follow" src="https://img.shields.io/badge/X-TauricResearch-white?logo=x&logoColor=white"/></a>
  <br>
  <a href="https://github.com/TauricResearch/" target="_blank"><img alt="Community" src="https://img.shields.io/badge/Join_GitHub_Community-TauricResearch-14C290?logo=discourse"/></a>
</div>

<div align="center">
  <!-- Keep these links. Translations will automatically update with the README. -->
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=de">Deutsch</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=es">Español</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=fr">français</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ja">日本語</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ko">한국어</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=pt">Português</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ru">Русский</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=zh">中文</a>
</div>

---

# TradingAgents: Multi-Agents LLM Financial Trading Framework 

> 🎉 **TradingAgents** officially released! We have received numerous inquiries about the work, and we would like to express our thanks for the enthusiasm in our community.
>
> So we decided to fully open-source the framework. Looking forward to building impactful projects with you!

<div align="center">
<a href="https://www.star-history.com/#TauricResearch/TradingAgents&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=TauricResearch/TradingAgents&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=TauricResearch/TradingAgents&type=Date" />
   <img alt="TradingAgents Star History" src="https://api.star-history.com/svg?repos=TauricResearch/TradingAgents&type=Date" style="width: 80%; height: auto;" />
 </picture>
</a>
</div>

<div align="center">

🚀 [TradingAgents](#tradingagents-framework) | ⚡ [Installation](#installation) | 🔄 [Running Analysis](#running-analysis) | 📦 [Package Usage](#tradingagents-package) | 🤝 [Contributing](#contributing) | 📄 [Citation](#citation)

</div>

## TradingAgents Framework

TradingAgents is a multi-agent trading framework that mirrors the dynamics of real-world trading firms. By deploying specialized LLM-powered agents: from fundamental analysts, sentiment experts, and technical analysts, to trader, risk management team, the platform collaboratively evaluates market conditions and informs trading decisions. Moreover, these agents engage in dynamic discussions to pinpoint the optimal strategy.

<p align="center">
  <img src="assets/schema.png" style="width: 100%; height: auto;">
</p>

> TradingAgents framework is designed for research purposes. Trading performance may vary based on many factors, including the chosen backbone language models, model temperature, trading periods, the quality of data, and other non-deterministic factors. [It is not intended as financial, investment, or trading advice.](https://tauric.ai/disclaimer/)

Our framework decomposes complex trading tasks into specialized roles. This ensures the system achieves a robust, scalable approach to market analysis and decision-making.

### Analyst Team
- Fundamentals Analyst: Evaluates company financials and performance metrics, identifying intrinsic values and potential red flags.
- Sentiment Analyst: Analyzes social media and public sentiment using sentiment scoring algorithms to gauge short-term market mood.
- News Analyst: Monitors global news and macroeconomic indicators, interpreting the impact of events on market conditions.
- Technical Analyst: Utilizes technical indicators (like MACD and RSI) to detect trading patterns and forecast price movements.

<p align="center">
  <img src="assets/analyst.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

### Researcher Team
- Comprises both bullish and bearish researchers who critically assess the insights provided by the Analyst Team. Through structured debates, they balance potential gains against inherent risks.

<p align="center">
  <img src="assets/researcher.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### Trader Agent
- Composes reports from the analysts and researchers to make informed trading decisions. It determines the timing and magnitude of trades based on comprehensive market insights.

<p align="center">
  <img src="assets/trader.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### Risk Management Team
- Continuously evaluates portfolio risk by assessing market volatility, liquidity, and other risk factors. The risk management team evaluates and adjusts trading strategies, providing assessment reports to guide final trading decisions.

<p align="center">
  <img src="assets/risk.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### Portfolio Manager Team (New!)
- **Portfolio Manager**: Generates personalized investment recommendations by combining TradingAgents analysis with the user's actual portfolio state (positions, transaction history, cash balance) stored in Google Sheets. Provides context-aware advice on:
  - Position sizing based on current allocation (e.g., "Add 10 shares" vs "Buy")
  - Diversification considerations (e.g., "You already have 15% in AAPL")
  - Risk management based on existing exposure (e.g., "Consider taking profits at $275")
  - Specific action recommendations with quantities: add, hold, reduce, or close positions

> **Example Output**: Instead of generic "BUY AAPL", the Portfolio Manager provides: *"You own 50 shares @ $240 (15% of portfolio, +$900 unrealized gain). **Add 10 shares** at current price (~$258). New allocation would be ~18% (max 20%). Consider taking partial profits at $275."*

## Installation

Clone TradingAgents:
```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
```

Create a virtual environment:
```bash
conda create -n tradingagents python=3.12
conda activate tradingagents
```

Install the package:
```bash
pip install -e .
```

### Configuration

Copy the example environment file and configure your API keys:
```bash
cp .env.example .env
```

Required API keys:
- **LLM_API_KEY** - Your LLM provider API key (OpenAI, Anthropic, etc.)
- **ALPHA_VANTAGE_API_KEY** - For market data and news ([get free key](https://www.alphavantage.co/support/#api-key))
- **GOOGLE_API_KEY** - For Google Search and embeddings ([get key](https://aistudio.google.com/))

Optional cloud storage (Cloudflare R2):
- **R2_ACCOUNT_ID**, **R2_ACCESS_KEY_ID**, **R2_SECRET_ACCESS_KEY** - R2 credentials
- **R2_BUCKET_NAME** - Bucket for storing reports
- **R2_PUBLIC_URL** - Public URL for permanent report access

### Portfolio Manager (Optional)

Enable personalized portfolio-aware trading recommendations by configuring Google Sheets integration:

```bash
# Enable Portfolio Manager
PORTFOLIO_MANAGER_ENABLED=true

# Google Sheets API
GOOGLE_SHEETS_CREDENTIALS=/path/to/credentials.json
GOOGLE_SHEET_ID=your_sheet_id

# Portfolio constraints (optional)
PORTFOLIO_MAX_POSITION_SIZE=0.20  # Max 20% per ticker
PORTFOLIO_MIN_CASH_RESERVE=0.10   # Keep 10% cash minimum
```

**Google Sheets Setup**:
1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project
2. Enable the Google Sheets API
3. Create a service account and download the credentials JSON file
4. Create a new Google Spreadsheet and copy its ID from the URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`
5. Share the spreadsheet with the service account email (from the credentials file)

The Portfolio Manager will automatically create three sheets in your spreadsheet:
- **Positions**: Current holdings with market value and unrealized P&L
- **Transactions**: Full transaction history (buy/sell orders)
- **Summary**: Portfolio metrics (total value, cash balance, daily P&L)

See `.env.example` for all available configuration options.

## Running Analysis

Analysis can be triggered manually or via external systems using GitHub Actions.

### Configure Tickers

Edit `tickers.txt` to specify default stocks to analyze:
```
AAPL
NVDA
TSLA
GOOGL
```

### GitHub Actions Setup

1. Add your API keys as GitHub Secrets (Settings > Secrets > Actions)
2. Trigger manually via Actions tab > "Run workflow"

Reports are uploaded to Cloudflare R2 with public URLs.

### External Trigger

Trigger analysis from any external system via HTTP:

```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/dispatches \
  -d '{"event_type": "run-analysis", "client_payload": {"tickers": "AAPL,NVDA"}}'
```

The `tickers` parameter is optional - if omitted, `tickers.txt` is used.

### Discord Notifications

Optionally receive notifications when analysis completes:

1. Create a webhook in Discord (Server Settings > Integrations > Webhooks)
2. Add `DISCORD_WEBHOOK_URL` to GitHub Secrets
3. Notifications include decision (BUY/SELL/HOLD) and report links

### TL;DR Summaries

All trading reports now include a **TL;DR (Too Long; Didn't Read)** summary at the top for quick reading:

```markdown
## TL;DR Summary

**Ticker:** AAPL | **Date:** 2026-01-10 | **Current Price:** $258.64

### Key Points
- **Recommendation:** BUY
- **RSI:** 25.95 (oversold)
- **50-day SMA:** $272.57
- **200-day SMA:** $232.80
- **MACD:** -3.34 (bearish)

### One-Line Summary
Deeply oversold conditions with RSI at 26 present buying opportunity within long-term uptrend...
```

The TL;DR automatically extracts key information from each report type:
- **Market Reports**: Current price, RSI, MACD, moving averages, recommendation
- **Fundamentals Reports**: Revenue, analyst ratings, key financial metrics
- **Final Decisions**: Trading decision, entry/stop/target levels, key arguments
- **Personalized Recommendations** (Portfolio Manager enabled): Current position, portfolio context, specific action with quantity

To disable TL;DR summaries, set `storage.include_tldr = False` in your configuration.

## Architecture Diagrams

Comprehensive PlantUML diagrams are available to help you understand the system architecture:

- **[High-Level Architecture](docs/diagrams/architecture.puml)** - Overall system architecture with major modules
- **[Agent Collaboration Flow](docs/diagrams/agent-flow.puml)** - Complete agent workflow from input to output
- **[Data Flow Diagram](docs/diagrams/data-flow.puml)** - How data flows through the system
- **[LangGraph State Machine](docs/diagrams/state-machine.puml)** - State transitions and execution flow
- **[Component Diagram](docs/diagrams/components.puml)** - Detailed component structure and interfaces
- **[Agent Class Hierarchy](docs/diagrams/agent-classes.puml)** - Inheritance relationships between agents
- **[Deployment Diagram](docs/diagrams/deployment.puml)** - System deployment architecture

### Viewing Diagrams

You can view the PlantUML diagrams using:
- **VS Code**: Install the [PlantUML extension](https://marketplace.visualstudio.com/items?items=jebbs.plantuml)
- **Online**: Paste the `.puml` content at [PlantUML Online](https://plantuml.com/plantuml/uml/)
- **CLI**: Install PlantUML and run `plantuml docs/diagrams/*.puml`

## TradingAgents Package

### Implementation Details

We built TradingAgents with LangGraph to ensure flexibility and modularity. We utilize `o1-preview` and `gpt-4o` as our deep thinking and fast thinking LLMs for our experiments. However, for testing purposes, we recommend you use `o4-mini` and `gpt-4.1-mini` to save on costs as our framework makes **lots of** API calls.

### Python Usage

To use TradingAgents inside your code, you can import the `tradingagents` module and initialize a `TradingAgentsGraph()` object. The `.propagate()` function will return a decision:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())

# forward propagate
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)
```

You can also adjust the default configuration to set your own choice of LLMs, debate rounds, etc.

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["deep_think_llm"] = "gpt-4.1-nano"  # Use a different model
config["quick_think_llm"] = "gpt-4.1-nano"  # Use a different model
config["max_debate_rounds"] = 1  # Increase debate rounds

# Configure data vendors (default uses yfinance and Alpha Vantage)
config["data_vendors"] = {
    "core_stock_apis": "yfinance",           # Options: yfinance, alpha_vantage, local
    "technical_indicators": "yfinance",      # Options: yfinance, alpha_vantage, local
    "fundamental_data": "alpha_vantage",     # Options: openai, alpha_vantage, local
    "news_data": "alpha_vantage",            # Options: openai, alpha_vantage, google, local
}

# Enable Portfolio Manager (optional, requires Google Sheets setup)
config["portfolio_manager"] = {
    "enabled": True,
    "google_sheets": {
        "credentials_path": "/path/to/credentials.json",
        "sheet_id": "your_sheet_id",
        "sheet_name": "Trading Portfolio",
    },
    "max_position_size": 0.20,  # Max 20% per ticker
    "min_cash_reserve": 0.10,   # Keep 10% cash minimum
}

# Initialize with custom config
ta = TradingAgentsGraph(debug=True, config=config)

# forward propagate
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)
```

> The default configuration uses yfinance for stock price and technical data, and Alpha Vantage for fundamental and news data. For production use or if you encounter rate limits, consider upgrading to [Alpha Vantage Premium](https://www.alphavantage.co/premium/) for more stable and reliable data access. For offline experimentation, there's a local data vendor option that uses our **Tauric TradingDB**, a curated dataset for backtesting, though this is still in development. We're currently refining this dataset and plan to release it soon alongside our upcoming projects. Stay tuned!

You can view the full list of configurations in `tradingagents/default_config.py`.

## Contributing

We welcome contributions from the community! Whether it's fixing a bug, improving documentation, or suggesting a new feature, your input helps make this project better. If you are interested in this line of research, please consider joining our open-source financial AI research community [Tauric Research](https://tauric.ai/).

## Citation

Please reference our work if you find *TradingAgents* provides you with some help :)

```
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework}, 
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138}, 
}
```
